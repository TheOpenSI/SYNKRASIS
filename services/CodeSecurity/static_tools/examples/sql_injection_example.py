#!/usr/bin/env python3
"""
Comprehensive Python vulnerability test file
Contains multiple types of security vulnerabilities for CodeQL testing
"""

import sqlite3
import os
import subprocess
import pickle
import tempfile

# Import Flask for web vulnerabilities (if available)
try:
    from flask import Flask, request, render_template_string
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# =============================================================================
# 1. SQL INJECTION VULNERABILITIES
# =============================================================================

def sql_injection_input():
    """SQL injection via input() - likely NOT detected by CodeQL"""
    conn = sqlite3.connect("example.db")
    cursor = conn.cursor()
    
    user_input = input("Enter username: ")
    # Vulnerable: Direct string concatenation
    query = "SELECT * FROM users WHERE username = '" + user_input + "'"
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

def sql_injection_parameter(username):
    """SQL injection via function parameter"""
    conn = sqlite3.connect("example.db")
    cursor = conn.cursor()
    
    # Vulnerable: String formatting
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

# Flask SQL injection (if Flask is available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    
    @app.route('/user')
    def get_user_web():
        """SQL injection via Flask request - SHOULD be detected by CodeQL"""
        username = request.args.get('username', '')
        conn = sqlite3.connect("example.db")
        cursor = conn.cursor()
        
        # Vulnerable: Direct string concatenation with web input
        query = "SELECT * FROM users WHERE username = '" + username + "'"
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return str(result)
    
    @app.route('/search')
    def search_users():
        """Another SQL injection via POST data"""
        search_term = request.form.get('search', '') if request.method == 'POST' else request.args.get('search', '')
        conn = sqlite3.connect("example.db")
        cursor = conn.cursor()
        
        # Vulnerable: % formatting
        query = "SELECT * FROM users WHERE name LIKE '%%%s%%'" % search_term
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return str(result)

# =============================================================================
# 2. COMMAND INJECTION VULNERABILITIES
# =============================================================================

def command_injection_input():
    """Command injection via input()"""
    filename = input("Enter filename to check: ")
    # Vulnerable: Direct command execution with user input
    result = os.system(f"ls -la {filename}")
    return result

def command_injection_subprocess():
    """Command injection via subprocess"""
    user_command = input("Enter command: ")
    # Vulnerable: Shell injection
    result = subprocess.run(f"echo {user_command}", shell=True, capture_output=True)
    return result.stdout

if FLASK_AVAILABLE:
    @app.route('/execute')
    def execute_command():
        """Command injection via web request - SHOULD be detected"""
        cmd = request.args.get('cmd', 'whoami')
        # Vulnerable: Direct command execution
        result = os.system(cmd)
        return f"Command executed with result: {result}"

# =============================================================================
# 3. PATH TRAVERSAL VULNERABILITIES
# =============================================================================

def path_traversal_input():
    """Path traversal via input()"""
    filename = input("Enter file to read: ")
    # Vulnerable: Direct file access without validation
    try:
        with open(f"/app/files/{filename}", 'r') as f:
            return f.read()
    except:
        return "File not found"

if FLASK_AVAILABLE:
    @app.route('/file')
    def read_file():
        """Path traversal via web request - SHOULD be detected"""
        filename = request.args.get('file', 'default.txt')
        # Vulnerable: Directory traversal
        try:
            with open(f"/app/data/{filename}", 'r') as f:
                return f.read()
        except:
            return "File not found"

# =============================================================================
# 4. DESERIALIZATION VULNERABILITIES
# =============================================================================

def unsafe_deserialization_input():
    """Unsafe pickle deserialization"""
    data = input("Enter pickled data (base64): ")
    import base64
    try:
        pickled_data = base64.b64decode(data)
        # Vulnerable: Unpickling user data
        result = pickle.loads(pickled_data)
        return result
    except:
        return "Invalid data"

if FLASK_AVAILABLE:
    @app.route('/deserialize', methods=['POST'])
    def deserialize_data():
        """Unsafe deserialization via web - SHOULD be detected"""
        data = request.get_data()
        # Vulnerable: Deserializing user-provided data
        try:
            result = pickle.loads(data)
            return str(result)
        except:
            return "Invalid data"

# =============================================================================
# 5. SERVER-SIDE TEMPLATE INJECTION
# =============================================================================

if FLASK_AVAILABLE:
    @app.route('/template')
    def template_injection():
        """Server-side template injection - SHOULD be detected"""
        template = request.args.get('template', 'Hello World')
        # Vulnerable: User input directly in template
        return render_template_string(template)

# =============================================================================
# 6. INSECURE FILE OPERATIONS
# =============================================================================

def insecure_temp_file():
    """Insecure temporary file creation"""
    # Vulnerable: Using predictable temp file names
    temp_filename = "/tmp/app_temp_" + str(os.getpid())
    with open(temp_filename, 'w') as f:
        f.write("sensitive data")
    return temp_filename

def insecure_file_permissions():
    """Insecure file permissions"""
    filename = "sensitive_config.txt"
    with open(filename, 'w') as f:
        f.write("database_password=secret123")
    # Vulnerable: World-readable permissions
    os.chmod(filename, 0o777)
    return filename

# =============================================================================
# 7. WEAK CRYPTOGRAPHY
# =============================================================================

def weak_crypto_example():
    """Weak cryptographic practices"""
    import hashlib
    password = input("Enter password: ")
    
    # Vulnerable: Using MD5 for password hashing
    weak_hash = hashlib.md5(password.encode()).hexdigest()
    
    # Vulnerable: Using a small key size
    key_size = 512  # Too small for RSA
    
    return weak_hash

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function demonstrating vulnerabilities"""
    print("=== Vulnerability Demonstration ===")
    
    print("\n1. Testing SQL Injection (input-based):")
    try:
        # This will prompt for input
        result = sql_injection_input()
        print(f"SQL result: {result}")
    except Exception as e:
        print(f"SQL error: {e}")
    
    print("\n2. Testing Command Injection:")
    try:
        # This will prompt for input
        result = command_injection_input()
        print(f"Command result: {result}")
    except Exception as e:
        print(f"Command error: {e}")
    
    print("\n3. Testing Path Traversal:")
    try:
        # This will prompt for input
        result = path_traversal_input()
        print(f"File content: {result[:100]}...")
    except Exception as e:
        print(f"File error: {e}")
    
    print("\n4. Testing Insecure Operations:")
    try:
        temp_file = insecure_temp_file()
        config_file = insecure_file_permissions()
        print(f"Created files: {temp_file}, {config_file}")
    except Exception as e:
        print(f"File operation error: {e}")
    
    # Flask app would need to be run separately
    if FLASK_AVAILABLE:
        print("\n5. Flask vulnerabilities available at:")
        print("   /user?username=<input>")
        print("   /execute?cmd=<command>") 
        print("   /file?file=<filename>")
        print("   /template?template=<template>")

if __name__ == "__main__":
    main()
    
    # Uncomment to run Flask app
    # if FLASK_AVAILABLE:
    #     app.run(debug=True, host='0.0.0.0')