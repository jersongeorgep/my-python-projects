list = []

for i in range(3):
    list.append([])
    for j in range(3):
        list[i].append(i+j)

print(list)
print(list[0][0])
print(list[1][2])