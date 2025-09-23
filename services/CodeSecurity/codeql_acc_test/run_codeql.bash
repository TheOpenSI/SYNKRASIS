#!/bin/bash

# download codeql zip if required
# wget https://github.com/github/codeql-action/releases/download/codeql-bundle-v2.23.0/codeql-bundle-linux64.tar.gz \
# -O ~/workspace_hcc4/codeql.tar.gz

PYTHON_DIR="$1"
CODEQL_BINARY="$2"
DATABASE_DIR="$3"
PROBLEM_ID="$4"
OUTPUT_DIR="services/CodeSecurity/codeql_acc_test/output_ql"

# help function
function show_help() {
    echo "Usage: $0 <python_directory> <codeql_binary_path> <database_dir> <problem_id>"
}

# show help if --help or incorrect args
if [ "$1" == "--help" ] || [ "$#" -ne 4 ]; then
    show_help
    exit 1
fi

# Validate inputs
if [ ! -e "$PYTHON_DIR" ] || [ ! -e "$CODEQL_BINARY" ]; then
    echo "Error: Python directory '$PYTHON_DIR' or CodeQL binary '$CODEQL_BINARY' does not exist."
    exit 1
fi

if [ -e "$DATABASE_DIR" ]; then
    echo "Database directory '$DATABASE_DIR' already exists."
    rm -rf "$DATABASE_DIR"
    echo "Removed existing database directory."
fi

# create codeql db
"$CODEQL_BINARY" database create "$DATABASE_DIR" --language=python --source-root="$PYTHON_DIR"

# analyze the python file
"$CODEQL_BINARY" database analyze "$DATABASE_DIR" codeql/python-queries \
--format=sarif-latest \
--output="$OUTPUT_DIR/results$PROBLEM_ID.sarif"