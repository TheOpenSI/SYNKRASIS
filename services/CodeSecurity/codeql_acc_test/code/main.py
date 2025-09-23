import os

def evaluate_input(user_input):
    # This function uses eval() to evaluate the user input as Python code.
    # If the user input is not properly sanitized, it can lead to arbitrary code execution.
    return eval(user_input)

def main():
    user_input = input("Enter some Python code to execute: ")
    result = evaluate_input(user_input)
    print("Result:", result)

if __name__ == "__main__":
    main()