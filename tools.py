from datetime import datetime, timedelta
from agents import function_tool,Runner
from pydantic import BaseModel
from typing import Dict, List
from rate_limiter import rate_limited_runner_call
from pydantic import BaseModel
from agents import Agent
from model_config import model as external_model
from dateutil import parser


class StudyPlan(BaseModel):
    subject: str
    exam_date: str
    plan: Dict[str,List[str]]

class ProgressReport(BaseModel):
    overall_score: float
    weak_topics: List[str]
    summaries: Dict[str, str]
    total_quizzes: int
    passed_quizzes: int
    failed_quizzes: int
    
class QuizResult(BaseModel):
    topic: str
    score: float

@function_tool
def generate_study_plan(subject: str, exam_date: str, topics: List[str]) -> StudyPlan:
    """
    Generate a structured day-by-day study plan from topics and exam date.
    Accepts natural date formats and assumes year = 2025 if not given.
    """

    try:
        # Try parsing date, assume default year = 2025 if not provided
        parsed_date = parser.parse(exam_date, default=datetime(2025, 1, 1))
        exam_dt = parsed_date.date()
    except Exception:
        return StudyPlan(subject=subject, exam_date=exam_date, plan={"error": ["Invalid exam date format"]})

    today = datetime.today().date()
    total_days = (exam_dt - today).days

    if total_days <= 0:
        return StudyPlan(subject=subject, exam_date=exam_date, plan={"error": ["Exam date must be in the future"]})

    plan = {}
    per_day = max(1, len(topics) // total_days)
    day = today
    i = 0

    while i < len(topics):
        assigned = topics[i:i + per_day]
        plan[day.strftime("%A %Y-%m-%d")] = assigned
        day += timedelta(days=1)
        i += per_day

    return StudyPlan(subject=subject, exam_date=exam_dt.isoformat(), plan=plan)

@function_tool
def summarize_topic(topic: str, summary: str) -> str:
    """
    Generate a short summary for a given topic using LLM response.

    Args:
    - topic (str): The topic to summarize.
    - summary (str): The LLM-generated summary of the topic.

    Returns:
    - str: A concise, structured summary including key concepts, formulas, and examples.
    """
    return f"Summary for {topic}: {summary}"

@function_tool
async def progress_tracker(results: List[QuizResult]) -> ProgressReport:
    """
    Analyze student's quiz results. Topics below 60% are marked weak.
    Summarizes weak topics using summarize_topic tool and returns a full progress report.
    """
    weak_topics = []
    summaries = {}

    for result in results:
        if result.score < 60:
            weak_topics.append(result.topic)

    # Run summarize_topic using Runner
    for topic in weak_topics:
        result = await rate_limited_runner_call(Runner.run,summarize_agent, topic)
        summaries[topic] = result.final_output

    report = ProgressReport(
        overall_score=sum(r.score for r in results) / len(results),
        weak_topics=weak_topics,
        summaries=summaries,
        total_quizzes=len(results),
        passed_quizzes=len([r for r in results if r.score >= 60]),
        failed_quizzes=len([r for r in results if r.score < 60]),
    )

    return report

@function_tool
async def quiz_evaluator(topic: str, answers: list[str]) -> str:
    """
    Evaluates a 10-question quiz on the given topic based on the user's answers (A, B, C, or D).
    Returns the score and explanations.
    """
    quiz = await rate_limited_runner_call(Runner.run, mcqs_generator, topic)
    questions = quiz.final_output.questions  # Fixed line

    if len(answers) != len(questions):
        return f"❌ Please provide {len(questions)} answers."

    score = 0
    result_lines = []

    for i, (q, user_ans) in enumerate(zip(questions, answers)):
        correct = q.answer.strip().upper()
        user = user_ans.strip().upper()

        if user == correct:
            score += 1
            result = "✅ Correct"
        else:
            result = f"❌ Incorrect (Correct: {correct})"

        result_lines.append(f"Q{i+1}: {result} - {q.question}")

    result_text = "\n".join(result_lines)
    return f"🎯 You scored {score}/{len(questions)}!\n\n{result_text}"

class MCQ(BaseModel):
    question: str
    options: list[str]
    answer: str
    
class MCQSet(BaseModel):
    topic: str
    questions: list[MCQ]





summarize_agent = Agent(
    name="Topic Summarizer",
    instructions="""
You are a helpful assistant that generates concise summaries using the summarize_topic tool for study topics.
Each summary should include:
- Key concepts
- Important formulas
- Relevant examples
Return results in a structured format.
""",
    model=external_model,
    tools=[summarize_topic],
)

mcqs_generator = Agent(
    name="MCQs Generator",
    instructions="""
You are a helpful assistant that generates high-quality multiple-choice questions (MCQs) for the given topic. 
Each question must include:
- A clear question stem
- 4 plausible options (labeled a-d)
- Only one correct answer

Do not generate more or fewer than 10 questions.
Return results in the format defined by the MCQSet schema.
""",
    output_type=MCQSet,
    model=external_model,
)
