
import ollama

print("Connecting to local AI model...")

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": "Explain what a Business Analyst does in simple words."
        }
    ]
)

print("\nAI Response:")
print(response["message"]["content"])
