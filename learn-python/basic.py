print("hello world")
age = 25
prince  = 19.95

name ="Jerson"
message = "Hello there"

is_active = True
is_admin = False

print (name, " is ", age, "years old")

a = 10
b = 3

print(a +b)
print (a - b)
print (a * b)
print(a / b)
print(a // b)
print (a % b)
print( a ** b)

fruits = ["apple", "banana", "cherry"]

# Access elements
print(fruits[0])  # apple
print(fruits[-1]) # cherry

# Modify list
fruits.append("orange")
fruits.insert(1, "grape")
fruits.remove("banana")

print(fruits)

with open("example.txt", "w") as file:
    file.write("Hello, File!")

# Read from file
with open("example.txt", "r") as file:
    content = file.read()
    print(content)

try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
finally:
    print("This always runs")