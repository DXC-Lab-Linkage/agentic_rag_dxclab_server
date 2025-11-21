# Batch Execution Guide

This guide explains how to use the batch execution functionality to process multiple questions in batch mode.

## Basic Usage

```bash
python batch_exec_graph_stream.py <input_file> [options]
```

Where `<input_file>` is a text file containing one question per line.

## Command Line Options

```
  -o, --output OUTPUT    Output file path (default: auto-generated)
  -f, --format {json,csv} Output format (default: json)
  --max-concurrent N     Maximum concurrent requests (default: 3)
  --single-chat          Use single chat session for all questions
  --delay SECONDS        Delay between requests in seconds (default: 1.0)
```

## Examples

### Basic Execution
```bash
python batch_exec_graph_stream.py sample_questions.txt
```

### With Options
```bash
python batch_exec_graph_stream.py sample_questions.txt \
    --single-chat \
    --delay 2.0 \
    --output results.json \
    --format json
```

## Input File Format

Create a text file with one question per line:

```
What is machine learning?
Can you give me an example?
How does it differ from traditional programming?
```

## Processing Modes

1. **Individual Chat Sessions (Default)**
   - Each question is processed independently
   - Use when questions are unrelated

2. **Single Chat Session (`--single-chat`)**
   - All questions share the same conversation context
   - Use when questions form a continuous conversation
