def calculator():
    print("Simple Calculator")
    print("Operations: +, -, *, /")
    
    num1 = float(input("Enter first number: "))
    operator = input("Enter operator: ")
    num2 = float(input("Enter second number: "))
    
    if operator == "+":
        result = num1 + num2
    elif operator == "-":
        result = num1 - num2
    elif operator == "*":
        result = num1 * num2
    elif operator == "/":
        if num2 == 0:
            print("Error: Division by zero!")
            return
        result = num1 / num2
    else:
        print("Invalid operator!")
        return
    
    print(f"Result: {result}")

calculator()

history = []

def calculator():
    while True:
        print("\n1. Calculate")
        print("2. View History")
        print("3. Exit")
        choice = input("Choose option: ")
        
        if choice == "1":
            num1 = float(input("First number: "))
            operator = input("Operator (+, -, *, /): ")
            num2 = float(input("Second number: "))
            
            if operator == "+":
                result = num1 + num2
            elif operator == "-":
                result = num1 - num2
            elif operator == "*":
                result = num1 * num2
            elif operator == "/":
                result = num1 / num2 if num2 != 0 else "Error: Division by zero"
            else:
                print("Invalid operator!")
                continue
            
            operation = f"{num1} {operator} {num2} = {result}"
            history.append(operation)
            print(operation)
        
        elif choice == "2":
            print("\nCalculation History:")
            for op in history:
                print(op)
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice!")

calculator()