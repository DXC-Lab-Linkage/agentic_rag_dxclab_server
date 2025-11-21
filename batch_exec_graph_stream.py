"""
Direct batch execution script for exec_graph_stream function
Executes multiple questions directly through the graph without API calls
"""

# Configuration flags
ENABLE_LOGGING = False  # Set to False to disable all logging output
ENABLE_FILE_OUTPUT = False  # Set to False to disable file output (console only)

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the src directory to the path to import modules
sys.path.append("src")

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

# Import the exec_graph_stream function directly
from routers.ask_agent import exec_graph_stream
from routers.utils.log_dev import LogDev
from schemas.app_schemas import ChatModel

# Load environment variables
load_dotenv()

# Suppress Faiss GPU warnings
os.environ["FAISS_ENABLE_GPU"] = "0"
import warnings

warnings.filterwarnings("ignore", message=".*GPU.*")

# Setup logging based on flag
if ENABLE_LOGGING:
    # Create log directory if it doesn't exist
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)

    # Setup logging with file and console output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir
                / f'batch_exec_graph_stream_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
            logging.StreamHandler(),
        ],
    )
else:
    # Disable logging completely
    logging.basicConfig(level=logging.CRITICAL + 1)  # Disable all logging

logger = logging.getLogger(__name__)


# Conditional logging function
def log_info(message: str):
    """Log message only if logging is enabled"""
    if ENABLE_LOGGING:
        logger.info(message)


def log_error(message: str):
    """Log error message only if logging is enabled"""
    if ENABLE_LOGGING:
        logger.error(message)


class MockRequest:
    """Mock Request object to simulate FastAPI Request"""

    def __init__(self, graph_app):
        self.app = MockApp(graph_app)


class MockApp:
    """Mock App object to hold the graph_app"""

    def __init__(self, graph_app):
        self.state = MockState(graph_app)


class MockState:
    """Mock State object to hold graph_app"""

    def __init__(self, graph_app):
        self.graph_app = graph_app


async def exec_graph_stream_with_history(
    request: ChatModel, req, msg_history: Optional[List] = None
):
    """
    Execute graph of Langgraph in stream mode with external message history

    Args:
        request (ChatModel): The current ChatModel object.
        req: The current request object.
        msg_history (Optional[List]): External message history to use instead of creating fresh
    """
    # If msg_history is provided, use it; otherwise create fresh with just the current question
    if msg_history is not None:
        # Add the new user request to existing history
        messages = msg_history.copy()
        messages.append(HumanMessage(content=request.user_request))
    else:
        # Original behavior - start fresh
        messages = [HumanMessage(content=request.user_request)]

    input_data = {
        "messages": messages,
        "turn": 1,
        "request": "",
        "rev_request": "",
        "plan": "",
        "plan_status": [],
        "plan_over": False,
        "plan_exec": "",
    }

    config = {"recursion_limit": 400, "configurable": {"thread_id": request.chat_id}}
    start_time = time.time()
    # The complete message is stored at the end of the Streaming messages
    last_comp_message = ""
    try:
        graph_app = req.app.state.graph_app
        async for mode, chunk in graph_app.astream(
            input_data, config, stream_mode=["messages", "custom", "updates"]
        ):
            if mode == "messages":
                message, meta = chunk
                # Stream messages.
                langgraph_node = meta.get("langgraph_node")
                if (
                    langgraph_node == "create_final_answer"
                    or langgraph_node == "ans_llm_solo"
                    or langgraph_node == "ask_human"
                ):
                    if ENABLE_LOGGING == True:
                        print(message.content, end="", flush=True)
                    data = {"type": "msg", "content": message.content}
                    yield f"{json.dumps(data)}\n\n"
            elif mode == "updates":
                pass
            elif mode == "custom":
                custom_event = chunk
                data = {"type": "custom", "content": custom_event}
                yield f"{json.dumps(data)}\n\n"
        # Get the complete message stored at the end of messages
        last_comp_message = message.content[1:-1]
        sanitized_answer = last_comp_message
        data = {"type": "final_msg", "content": sanitized_answer}
        yield f"{json.dumps(data)}\n\n"
    except Exception as err:
        import traceback

        full_traceback = traceback.format_exc()
        print("=" * 80)
        print("FULL ERROR TRACEBACK:")
        print(full_traceback)
        print("=" * 80)
        print(f"Error type: {type(err).__name__}")
        print(f"Error message: {err}")

        data = {
            "type": "error",
            "content": "Error: An error occurred while running the Agent.",
            "detail": str(err),
            "traceback": full_traceback,
        }
        yield f"{json.dumps(data)}\n\n"
        raise Exception(err)
    end_time = time.time()
    elapsed_time = end_time - start_time
    log_info("\n-- Elapsed time --")
    elapsed_str = f"Elapsed time:" + "{:.1f}".format(elapsed_time) + "(s)"
    log_info(elapsed_str)
    data = {"type": "custom", "content": elapsed_str}
    yield f"{json.dumps(data)}\n\n"


class BatchGraphStreamExecutor:
    """Batch executor for direct exec_graph_stream calls"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.results: List[Dict[str, Any]] = []
        self.graph_app = None
        self.chat_histories: Dict[str, List] = {}  # Store chat histories by chat_id

    async def initialize_graph_app(self):
        """Initialize the graph application"""
        try:
            # Import and initialize the graph app similar to main.py
            from routers.agentic_rag.auto_rag_agent import AutoRagAgent

            auto_rag_agent = AutoRagAgent()
            self.graph_app = await auto_rag_agent.create_graph()
            logger.info("Graph application initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize graph application: {e}")
            return False

    async def parse_stream_response(self, generator) -> Dict[str, Any]:
        """Parse the streaming response from exec_graph_stream"""
        messages = []
        custom_events = []
        final_answer = ""
        error_info = None

        try:
            async for line in generator:
                if line.strip():
                    try:
                        # Remove the trailing newlines
                        clean_line = line.rstrip("\n")
                        data = json.loads(clean_line)
                        msg_type = data.get("type", "")
                        content = data.get("content", "")

                        if msg_type == "msg":
                            messages.append(content)
                        elif msg_type == "custom":
                            custom_events.append(content)
                        elif msg_type == "final_msg":
                            final_answer = content
                        elif msg_type == "error":
                            error_info = {
                                "message": content,
                                "detail": data.get("detail", ""),
                                "traceback": data.get("traceback", ""),
                            }
                            break

                    except json.JSONDecodeError:
                        # Skip lines that aren't valid JSON
                        continue

        except Exception as e:
            error_info = {
                "message": f"Error parsing stream response: {str(e)}",
                "detail": "",
                "traceback": "",
            }

        return {
            "messages": messages,
            "custom_events": custom_events,
            "final_answer": final_answer,
            "error": error_info,
            "full_response": "".join(messages) if messages else final_answer,
        }

    async def execute_single_question(
        self,
        question: str,
        chat_id: str,
        question_id: Optional[str] = None,
        msg_history: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Execute a single question through exec_graph_stream with optional message history"""
        start_time = time.time()

        # Create ChatModel request
        request = ChatModel(
            chat_id=chat_id, user_request=question, answer="", chat_start_date=""
        )

        # Create mock request object
        mock_request = MockRequest(self.graph_app)

        try:
            logger.info(
                f"Processing question {question_id or 'N/A'}: {question[:100]}..."
            )

            # Use the new function with message history support
            generator = exec_graph_stream_with_history(
                request, mock_request, msg_history
            )

            # Parse the streaming response
            parsed_response = await self.parse_stream_response(generator)
            processing_time = time.time() - start_time

            if parsed_response["error"]:
                result = {
                    "question_id": question_id,
                    "question": question,
                    "chat_id": chat_id,
                    "status": "error",
                    "error": parsed_response["error"]["message"],
                    "error_detail": parsed_response["error"]["detail"],
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat(),
                }
                logger.error(
                    f"Graph error for question {question_id or 'N/A'}: {parsed_response['error']['message']}"
                )
            else:
                # Update chat history for this chat_id if successful
                if chat_id not in self.chat_histories:
                    self.chat_histories[chat_id] = []

                # Add the human message and AI response to history
                self.chat_histories[chat_id].append(HumanMessage(content=question))
                final_answer = (
                    parsed_response["final_answer"] or parsed_response["full_response"]
                )
                self.chat_histories[chat_id].append(AIMessage(content=final_answer))

                result = {
                    "question_id": question_id,
                    "question": question,
                    "chat_id": chat_id,
                    "status": "success",
                    "answer": final_answer,
                    "messages": parsed_response["messages"],
                    "custom_events": parsed_response["custom_events"],
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat(),
                }
                logger.info(
                    f"Successfully processed question {question_id or 'N/A'} in {processing_time:.2f}s"
                )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            result = {
                "question_id": question_id,
                "question": question,
                "chat_id": chat_id,
                "status": "error",
                "error": str(e),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
            }

            logger.error(f"Exception processing question {question_id or 'N/A'}: {e}")
            return result

    async def process_batch(
        self,
        questions: List[Dict[str, Any]],
        use_single_chat: bool = False,
        delay_between_requests: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Process a batch of questions"""

        logger.info(f"Starting batch processing of {len(questions)} questions")

        # Setup chat IDs
        if use_single_chat:
            # Use single chat ID for all questions
            chat_id = f"chat_{uuid.uuid4().hex[:8]}"
            logger.info(f"Using single chat session: {chat_id}")
            for question in questions:
                question["chat_id"] = chat_id
        else:
            # Create individual chat IDs for each question
            logger.info("Creating individual chat sessions for each question")
            for question in questions:
                question["chat_id"] = f"chat_{uuid.uuid4().hex[:8]}"

        # Process questions with concurrency control
        if use_single_chat:
            # For single chat sessions, process sequentially to maintain conversation order
            logger.info(
                "Processing questions sequentially to maintain conversation order"
            )
            results = []
            for question_data in questions:
                chat_id = question_data["chat_id"]
                msg_history = self.chat_histories.get(chat_id, None)

                result = await self.execute_single_question(
                    question=question_data["question"],
                    chat_id=chat_id,
                    question_id=question_data.get("question_id"),
                    msg_history=msg_history,
                )
                results.append(result)

                # Add delay between requests
                if delay_between_requests > 0:
                    await asyncio.sleep(delay_between_requests)
        else:
            # For separate chat sessions, use concurrent processing
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def process_with_semaphore(
                question_data: Dict[str, Any],
            ) -> Dict[str, Any]:
                async with semaphore:
                    # Get message history for this chat_id if it exists
                    chat_id = question_data["chat_id"]
                    msg_history = self.chat_histories.get(chat_id, None)

                    result = await self.execute_single_question(
                        question=question_data["question"],
                        chat_id=chat_id,
                        question_id=question_data.get("question_id"),
                        msg_history=msg_history,
                    )

                    # Add delay between requests
                    if delay_between_requests > 0:
                        await asyncio.sleep(delay_between_requests)

                    return result

            # Execute all tasks
            logger.info(
                f"Starting concurrent processing with max {self.max_concurrent} concurrent requests"
            )
            tasks = [process_with_semaphore(q) for q in questions]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "question_id": questions[i].get("question_id"),
                    "question": questions[i]["question"],
                    "status": "error",
                    "error": str(result),
                    "timestamp": datetime.now().isoformat(),
                }
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        self.results = processed_results
        logger.info(
            f"Batch processing completed. {len(processed_results)} results generated."
        )
        return processed_results


def load_questions_from_txt(file_path: str) -> List[Dict[str, Any]]:
    """Load questions from text file (one question per line)"""
    questions = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:  # Skip empty lines
                question_data = {"question_id": f"q_{i+1}", "question": line}
                questions.append(question_data)

    return questions


def save_results_to_json(results: List[Dict[str, Any]], output_path: str):
    """Save results to JSON file"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def save_results_to_csv(results: List[Dict[str, Any]], output_path: str):
    """Save results to CSV file"""
    if not results:
        return

    fieldnames = [
        "question_id",
        "question",
        "chat_id",
        "status",
        "answer",
        "processing_time",
        "timestamp",
        "error",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Truncate long answers for CSV readability
            answer = result.get("answer", "")
            if len(answer) > 500:
                answer = answer[:500] + "..."

            row = {
                "question_id": result.get("question_id", ""),
                "question": result.get("question", ""),
                "chat_id": result.get("chat_id", ""),
                "status": result.get("status", ""),
                "answer": answer,
                "processing_time": result.get("processing_time", ""),
                "timestamp": result.get("timestamp", ""),
                "error": result.get("error", ""),
            }
            writer.writerow(row)


def print_summary(results: List[Dict[str, Any]]):
    """Print execution summary"""
    total = len(results)
    success = len([r for r in results if r.get("status") == "success"])
    errors = total - success

    total_time = sum(r.get("processing_time", 0) for r in results)
    avg_time = total_time / total if total > 0 else 0

    print("\n" + "=" * 60)
    print("BATCH GRAPH EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total questions: {total}")
    print(f"Successful: {success}")
    print(f"Failed: {errors}")
    print(f"Success rate: {success/total*100:.1f}%" if total > 0 else "N/A")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average processing time: {avg_time:.2f}s")
    print("=" * 60)

    # Show all final answers
    print("\nAll Question Results:")
    print("=" * 80)
    for i, result in enumerate(results, 1):
        question = result.get("question", "N/A")
        status = result.get("status", "unknown")

        print(f"Question {i}: {question}")
        print(f"Status: {status}")

        if status == "success":
            answer = result.get("answer", "No answer available")
            print(f"Final Answer: {answer}")
        else:
            error = result.get("error", "Unknown error")
            print(f"Error: {error}")

        print("-" * 80)

    if errors > 0:
        print("Error summary:")
        error_results = [r for r in results if r.get("status") == "error"]
        error_types = {}
        for result in error_results:
            error = result.get("error", "Unknown error")
            error_types[error] = error_types.get(error, 0) + 1

        for error, count in error_types.items():
            print(f"  {error}: {count} occurrences")


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Direct batch execution for graph stream"
    )
    parser.add_argument("input_file", help="Input file (TXT format only)")
    parser.add_argument(
        "-o", "--output", help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "-f", "--format", choices=["json", "csv"], default="json", help="Output format"
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=3, help="Maximum concurrent requests"
    )
    parser.add_argument(
        "--single-chat",
        action="store_true",
        help="Use single chat session for all questions",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests (seconds)"
    )

    args = parser.parse_args()

    # Load questions
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)

    try:
        if input_path.suffix.lower() == ".txt":
            questions = load_questions_from_txt(args.input_file)
        else:
            print("Error: Input file must be TXT format")
            sys.exit(1)

        logger.info(f"Loaded {len(questions)} questions from {args.input_file}")

    except Exception as e:
        print(f"Error loading questions: {e}")
        sys.exit(1)

    # Generate output filename if not provided
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"batch_graph_results_{timestamp}.{args.format}"

    # Initialize executor
    executor = BatchGraphStreamExecutor(max_concurrent=args.max_concurrent)

    # Initialize graph application
    if not await executor.initialize_graph_app():
        print("Error: Failed to initialize graph application")
        sys.exit(1)

    # Process questions
    try:
        print(f"Starting direct graph batch processing...")
        print(f"Input file: {args.input_file}")
        print(f"Output file: {output_path}")
        print(f"Max concurrent: {args.max_concurrent}")
        print(f"Single chat session: {args.single_chat}")
        print(f"Delay between requests: {args.delay}s")
        print("-" * 60)

        results = await executor.process_batch(
            questions=questions,
            use_single_chat=args.single_chat,
            delay_between_requests=args.delay,
        )

        # Save results based on flag
        if ENABLE_FILE_OUTPUT:
            if args.format == "json":
                save_results_to_json(results, output_path)
            else:
                save_results_to_csv(results, output_path)
            print(f"\nResults saved to: {output_path}")
        else:
            print(f"\nFile output is disabled (ENABLE_FILE_OUTPUT = False)")

        # Print summary
        print_summary(results)

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
