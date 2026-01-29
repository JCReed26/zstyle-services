from openmemory import OpenMemory

client = OpenMemory(mode="remote", url="http://localhost:8080")

client.add("Hello world")
print(client.query("Hello"))