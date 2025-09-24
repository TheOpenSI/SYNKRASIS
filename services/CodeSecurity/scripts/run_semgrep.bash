#!/bin/bash

# Exit on any error
set -e

PYTHON_DIR="$1"
OUTPUT_FILE="$2"
VERBOSE_FLAG="$3"

# Help function
function show_help() {
    echo "Usage: $0 <python_directory> <output_file> [--verbose]"
    echo ""
    echo "Arguments:"
    echo "  python_directory    Directory containing Python code to analyse"
    echo "  output_file_name    Name for the output file"
    echo "  --verbose           (Optional) Show Semgrep output during scan"
    echo ""
    echo "Example:"
    echo "  $0 ./my_code output_dir/file.json --verbose"
}

# Show help if --help or incorrect args
if [ "$1" == "--help" ] || [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    show_help
    exit 1
fi

# Validate verbose flag if provided
if [ "$#" -eq 3 ] && [ "$VERBOSE_FLAG" != "--verbose" ]; then
    echo "Error: Invalid flag '$VERBOSE_FLAG'. Use --verbose or omit for quiet mode."
    exit 1
fi

# Validate Python directory exists
if [ ! -e "$PYTHON_DIR" ]; then
    echo "Error: Python directory '$PYTHON_DIR' does not exist."
    exit 1
fi

# Determine verbosity
if [ "$VERBOSE_FLAG" == "--verbose" ]; then
    QUIET_FLAG=""
    echo "Running Semgrep in verbose mode..."
else
    QUIET_FLAG="--quiet"
    echo "Running Semgrep analysis..."
fi

# Run Semgrep with multiple configs
semgrep --config p/python \
        --config p/security-audit \
        --config p/owasp-top-ten \
        --config p/bandit \
        --json \
        --output="$OUTPUT_FILE" \
        $QUIET_FLAG \
        "$PYTHON_DIR"

echo "Analysis complete. Results saved to: $OUTPUT_FILE"