import os
import uuid
import json
import smtplib
import logging
import time
from pathlib import Path
from typing import List
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# JSON file paths
USERS_FILE = DATA_DIR / "users.json"
QUIZ_SUBMISSIONS_FILE = DATA_DIR / "quiz_submissions.json"
PDF_FILES_FILE = DATA_DIR / "pdf_files.json"
CHAPTER_OBSERVATIONS_FILE = DATA_DIR / "chapter_observations.json"

# Initialize JSON files if they don't exist
def init_json_file(file_path: Path, default_data: list = None):
    if not file_path.exists():
        with open(file_path, 'w') as f:
            json.dump(default_data or [], f)

# Initialize all JSON files
init_json_file(USERS_FILE)
init_json_file(QUIZ_SUBMISSIONS_FILE)
init_json_file(PDF_FILES_FILE)
init_json_file(CHAPTER_OBSERVATIONS_FILE)

# Helper functions for JSON operations
def read_json_file(file_path: Path) -> list:
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json_file(file_path: Path, data: list):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def find_one(data_list: list, query: dict) -> dict:
    for item in data_list:
        if all(item.get(k) == v for k, v in query.items()):
            return item
    return None

def update_one(data_list: list, query: dict, update: dict) -> bool:
    for i, item in enumerate(data_list):
        if all(item.get(k) == v for k, v in query.items()):
            data_list[i].update(update)
            return True
    return False

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://yi.crivo.in",
        "http://localhost",
        "http://bhubs.crivo.in",
        "https://bhubs.crivo.in",
        "https://yi.crivo.in",
        "http://chotacop.crivo.in",
        "https://chotacop.crivo.in",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://148.135.137.228:5000",
        "https://chotacop.in",
        "https://www.chotacop.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QuizSubmission(BaseModel):
    email: str
    chapter: str
    name: str
    school: str
    class_: str
    q1: List[int]
    q2: List[int]
    q3: List[int]
    q4: List[int]
    q5: List[int]
    q6: List[int]
    q7: List[int]
    q8: List[int]
    q9: List[int]
    q10: List[int]
    q11: List[int]
    q12: List[int]
    q13: List[int]
    c1: int
    c2: int
    c3: int
    c4: int
    c5: int

class BulkSubmissionItem(BaseModel):
    q1: List[int]
    q2: List[int]
    q3: List[int]
    q4: List[int]
    q5: List[int]
    q6: List[int]
    q7: List[int]
    q8: List[int]
    q9: List[int]
    q10: List[int]
    q11: List[int]
    q12: List[int]
    q13: List[int]
    c1: int
    c2: int
    c3: int
    c4: int
    c5: int

class BulkUploadRequest(BaseModel):
    chapter: str
    school: str
    submissions: List[BulkSubmissionItem]

class SignUpRequest(BaseModel):
    email: EmailStr
    chapter_name: str

class SignInRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    email: str
    user_id: str
    chapter: str

class SendOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    



last_push_time = 0

def sync_git(commit_message: str = "Auto sync from API"):
    global last_push_time
    now = time.time()
    if now - last_push_time < 10:
        return  # Avoid pushing too often
    last_push_time = now
    try:
        os.system("git add .")
        os.system(f'git commit --allow-empty -m "{commit_message}"')
        os.system("git push origin main > /dev/null 2>&1")  # Silent push
        logger.info("✅ Git synced successfully.")
    except Exception as e:
        logger.error(f"❌ Git sync failed: {e}")

# API: Signup
@app.post("/signup", response_model=UserResponse)
async def signup(request: SignUpRequest):
    users = read_json_file(USERS_FILE)
    
    if find_one(users, {"email": request.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if find_one(users, {"chapter": request.chapter_name}):
        raise HTTPException(status_code=400, detail="Chapter already registered")

    user = {
        "email": request.email,
        "user_id": str(uuid.uuid4()),
        "chapter": request.chapter_name,
        "created_at": datetime.utcnow().isoformat()
    }
    users.append(user)
    write_json_file(USERS_FILE, users)
    logger.info(f"User signed up: {request.email}")
    sync_git("Auto sync from /signup")
    return user

# API: Signin
@app.post("/signin", response_model=UserResponse)
async def signin(request: SignInRequest):
    users = read_json_file(USERS_FILE)
    user = find_one(users, {"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User signed in: {request.email}")
    return user

@app.post("/api/signin", response_model=UserResponse)
async def api_signin(request: SignInRequest):
    return await signin(request)

# API: Upload Quiz
@app.post("/upload")
async def upload_quiz(data: QuizSubmission):
    quiz = data.dict()
    quiz["class"] = quiz.pop("class_")
    quiz["created_at"] = datetime.utcnow().isoformat()
    
    submissions = read_json_file(QUIZ_SUBMISSIONS_FILE)
    existing_submission = find_one(submissions, {"email": quiz["email"]})
    
    if existing_submission:
        update_one(submissions, {"email": quiz["email"]}, quiz)
        logger.info(f"Quiz updated for: {quiz['email']}")
    else:
        submissions.append(quiz)
        logger.info(f"Quiz submitted for: {quiz['email']}")
    
    write_json_file(QUIZ_SUBMISSIONS_FILE, submissions)
    sync_git("Auto sync from /upload")
    return {"message": "Quiz submission saved successfully"}

# API: Check if Email Exists
@app.post("/check-mail")
async def check_email_exists(email: str = Body(..., embed=True)):
    submissions = read_json_file(QUIZ_SUBMISSIONS_FILE)
    exists = bool(find_one(submissions, {"email": email}))
    logger.info(f"Checked email existence in quiz submissions: {email}, exists: {exists}")
    return {"exists": exists}

# API: Get All Quiz Submissions for Email
@app.post("/email-data")
async def get_data_by_email(email: str = Body(..., embed=True)):
    submissions = read_json_file(QUIZ_SUBMISSIONS_FILE)
    data = [s for s in submissions if s["email"] == email]
    logger.info(f"Retrieved quiz data for: {email}")
    return {"data": data}

# API: Send OTP
@app.post("/send-otp")
async def send_otp(otp_request: SendOTPRequest):
    logger.info(f"Attempting to send OTP to: {otp_request.email}, OTP: {otp_request.otp}")
    result = send_otp_via_gmail(otp_request.otp, otp_request.email)
    if result == "OTP sent successfully":
        logger.info(f"OTP sent successfully to: {otp_request.email}")
        return {"message": "OTP sent successfully"}
    else:
        logger.error(f"Failed to send OTP to: {otp_request.email}, error: {result}")
        raise HTTPException(status_code=500, detail=result)

# Helper: Send OTP via Gmail
def send_otp_via_gmail(otp, recipient_email):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "chotacopyi@gmail.com"
    sender_password = "tfgn wtua dygg zbmf"

    if not sender_password:
        return "Failed to send OTP: GMAIL_APP_PASSWORD not set"

    try:
        subject = "Your OTP Code"
        body = f"Hi,\n\nYour OTP is: {otp}\n\nThanks,\nChotaCop Team"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return "OTP sent successfully"

    except Exception as e:
        return f"Failed to send OTP: {str(e)}"

# API: Send PDF
@app.post("/send-pdf")
async def send_pdf(file: UploadFile = File(...), email: str = Form(...)):
    file_data = await file.read()
    pdf_files = read_json_file(PDF_FILES_FILE)
    
    pdf_entry = {
        "filename": file.filename,
        "content": file_data.hex(),  # Convert bytes to hex string for JSON storage
        "email": email,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    pdf_files.append(pdf_entry)
    write_json_file(PDF_FILES_FILE, pdf_files)
    
    # Convert hex string back to bytes for email
    file_data = bytes.fromhex(pdf_entry["content"])
    print(email)
    result = await send_pdf_via_gmail(file_data, email)
    logger.info(f"PDF sent to: {email}, result: {result}")
    return {"message": result}

# Helper: Send Email with PDF
async def send_pdf_via_gmail(pdf_data, recipient_email):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "chotacopyi@gmail.com"
    sender_password = "tfgn wtua dygg zbmf"

    if not sender_password:
        return "Failed to send PDF: GMAIL_APP_PASSWORD not set"

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = "Your PDF File"
        msg.attach(MIMEText("Hi,\n\nPlease find the attached PDF.\n\nThanks! from Crivo", "plain"))

        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment; filename=document.pdf")
        msg.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return "PDF sent successfully"
    except Exception as e:
        return f"Failed to send PDF: {str(e)}"

# API: Update Chapter Observation
@app.post("/update-observation")
async def update_observation(request: Request):
    body = await request.json()
    chapter = body.get("chapter")
    data = body.get("data")

    if not chapter or not data:
        raise HTTPException(status_code=400, detail="Missing 'chapter' or 'data'")

    observations = read_json_file(CHAPTER_OBSERVATIONS_FILE)
    existing_observation = find_one(observations, {"chapter": chapter})
    
    if existing_observation:
        update_one(observations, {"chapter": chapter}, {
            "data": data,
            "updated_at": datetime.utcnow().isoformat()
        })
    else:
        observations.append({
            "chapter": chapter,
            "data": data,
            "updated_at": datetime.utcnow().isoformat()
        })
    
    write_json_file(CHAPTER_OBSERVATIONS_FILE, observations)
    logger.info(f"Updated observation for chapter: {chapter}")
    sync_git("Auto sync from /update-observation")
    return {"message": "Observation data added or updated"}


# API: Get Combined Chapter Data (Observations and Question Stats)
@app.post("/chapter-data")
async def get_chapter_data(payload: dict = Body(...)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing 'user_id'")

    # Get user's chapter
    users = read_json_file(USERS_FILE)
    user = find_one(users, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chapter = user["chapter"]
    
    # Get all data
    submissions = read_json_file(QUIZ_SUBMISSIONS_FILE)
    observations = read_json_file(CHAPTER_OBSERVATIONS_FILE)
    
    # If chapter is ALL_Chapter, return all data
    if chapter == "ALL_Chapter":
        # Get unique chapters from both submissions and observations
        chapters = list(set(s["chapter"] for s in submissions) | set(o["chapter"] for o in observations))
        chapters.sort()  # Sort chapters alphabetically
        
        all_chapter_data = {}
        for chapter_name in chapters:
            # Get submissions for this chapter
            chapter_submissions = [s for s in submissions if s["chapter"] == chapter_name]
            
            # Get observation for this chapter
            chapter_observation = find_one(observations, {"chapter": chapter_name})
            
            # Initialize stats dictionary for this chapter
            chapter_stats = {}
            
            # Calculate stats for each question (q1 through q13)
            for q_num in range(1, 14):
                q_key = f"q{q_num}"
                question_stats = {
                    "total_submissions": len(chapter_submissions),
                    "rides": {}
                }
                
                # Calculate stats for each ride (0-6)
                for ride_index in range(7):
                    ones = sum(1 for submission in chapter_submissions 
                              if len(submission[q_key]) > ride_index and submission[q_key][ride_index] == 1)
                    zeros = sum(1 for submission in chapter_submissions 
                               if len(submission[q_key]) > ride_index and submission[q_key][ride_index] == 0)
                    
                    question_stats["rides"][f"ride_{ride_index}"] = {
                        "ones": ones,
                        "zeros": zeros,
                        "total": ones + zeros
                    }
                
                chapter_stats[q_key] = question_stats
            
            # Combine all data for this chapter
            all_chapter_data[chapter_name] = {
                "total_submissions": len(chapter_submissions),
                "question_stats": chapter_stats,
                "observation": chapter_observation["data"] if chapter_observation else None
            }
        
        logger.info(f"Retrieved combined data for all chapters")
        return {
            "chapter": "ALL_Chapter",
            "chapters": all_chapter_data
        }
    
    # For specific chapter, return combined data
    chapter_submissions = [s for s in submissions if s["chapter"] == chapter]
    chapter_observation = find_one(observations, {"chapter": chapter})
    
    if not chapter_submissions and not chapter_observation:
        return {
            "chapter": chapter,
            "total_submissions": 0,
            "question_stats": {},
            "observation": None
        }
    
    # Initialize stats dictionary
    stats = {}
    
    # Calculate stats for each question (q1 through q13)
    for q_num in range(1, 14):
        q_key = f"q{q_num}"
        question_stats = {
            "total_submissions": len(chapter_submissions),
            "rides": {}
        }
        
        # Calculate stats for each ride (0-6)
        for ride_index in range(7):
            ones = sum(1 for submission in chapter_submissions 
                      if len(submission[q_key]) > ride_index and submission[q_key][ride_index] == 1)
            zeros = sum(1 for submission in chapter_submissions 
                       if len(submission[q_key]) > ride_index and submission[q_key][ride_index] == 0)
            
            question_stats["rides"][f"ride_{ride_index}"] = {
                "ones": ones,
                "zeros": zeros,
                "total": ones + zeros
            }
        
        stats[q_key] = question_stats
    
    logger.info(f"Retrieved combined data for chapter: {chapter}")
    return {
        "chapter": chapter,
        "total_submissions": len(chapter_submissions),
        "question_stats": stats,
        "observation": chapter_observation["data"] if chapter_observation else None
    }

# API: Bulk Upload Quiz Submissions
@app.post("/bulk-upload")
async def bulk_upload_quiz(data: BulkUploadRequest):
    submissions = read_json_file(QUIZ_SUBMISSIONS_FILE)
    
    # Process each submission in the bulk upload
    for submission in data.submissions:
        # Create a new submission entry
        new_submission = {
            "email": f"bulk_{datetime.utcnow().timestamp()}_{len(submissions)}",  # Generate unique email
            "chapter": data.chapter,
            "name": f"Bulk Submission {len(submissions) + 1}",
            "school": data.school,
            "class": "Bulk",  # Default class for bulk submissions
            "q1": submission.q1,
            "q2": submission.q2,
            "q3": submission.q3,
            "q4": submission.q4,
            "q5": submission.q5,
            "q6": submission.q6,
            "q7": submission.q7,
            "q8": submission.q8,
            "q9": submission.q9,
            "q10": submission.q10,
            "q11": submission.q11,
            "q12": submission.q12,
            "q13": submission.q13,
            "c1": submission.c1,
            "c2": submission.c2,
            "c3": submission.c3,
            "c4": submission.c4,
            "c5": submission.c5,
            "created_at": datetime.utcnow().isoformat()
        }
        
        submissions.append(new_submission)
    
    write_json_file(QUIZ_SUBMISSIONS_FILE, submissions)
    logger.info(f"Bulk uploaded {len(data.submissions)} quiz submissions for chapter: {data.chapter}, school: {data.school}")
    sync_git("Auto sync from /bulk-upload")
    return {"message": f"Successfully uploaded {len(data.submissions)} quiz submissions"}

@app.get("/")
def read_root():
    return {"message": "Hello, from FastAPI!"}