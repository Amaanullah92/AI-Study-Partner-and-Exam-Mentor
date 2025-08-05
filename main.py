import chainlit as cl
from model_config import config
from agents import Agent, Runner
from tools import quiz_evaluator, progress_tracker, generate_study_plan
from tools import mcqs_generator, summarize_agent
from openai.types.responses import ResponseTextDeltaEvent
from rate_limiter import rate_limited_runner_call_sync

main_agent = Agent(
    name="AI Study Partner & Exam Mentor",
    instructions="""
You are a helpful AI Study Partner that helps students prepare for exams and assist with academic queries or study-related tasks, including simple subject questions.

You can:
- Conduct quizzes using Quiz Conductor.
- Track quiz progress using Progress Tracker tool.
- Generate study plans.
- Summarize topics.
- Answer academic subject-related questions, even if simple.
- Redirect or reject clearly off-topic questions (e.g., personal, entertainment, or unrelated tech queries).
""",
    tools=[
        mcqs_generator.as_tool(
            tool_name="mcqs_generator",
            tool_description="Generates multiple-choice questions for a given topic."
        ),
        quiz_evaluator,
        progress_tracker,
        generate_study_plan,
        summarize_agent.as_tool(
            tool_name="summarize_topic",
            tool_description="Summarizes a given topic."
        ),
    ],
)

conversation_history = []

@cl.on_chat_start
async def on_chat_start():
    global conversation_history
    conversation_history = []
    await cl.Message(content="👋 Welcome! I'm your AI Study Partner. How can I assist you today?").send()

@cl.on_message
async def handle_message(message: cl.Message):
    global conversation_history


    if message.elements:
        await cl.Message(content="❌ I can’t read uploaded files. Please copy-paste the text or describe the content.").send()
        return


    conversation_history.append({"role": "user", "content": message.content})
    formatted_prompt = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
        for msg in conversation_history
    )

    try:
        final_msg = cl.Message(author="AI", content="")
        await final_msg.send()

        result = rate_limited_runner_call_sync(
            Runner.run_streamed, main_agent, formatted_prompt, run_config=config
        )

        full_response = ""
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta = event.data.delta or ""
                full_response += delta
                await final_msg.stream_token(delta)

        await final_msg.update()
        conversation_history.append({"role": "assistant", "content": full_response})

    except Exception as e:
        await cl.Message(content=f"❌ Error: {e}").send()
