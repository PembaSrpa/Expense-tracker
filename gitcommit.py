import subprocess

def git_push(message):
    try:
        # # 1. Generate requirements.txt
        # print("Updating requirements.txt...")
        # with open("requirements.txt", "w") as f:
        #     subprocess.run(["pip", "freeze"], stdout=f, check=True)

        # 2. Stage all changes (including the new requirements.txt)
        subprocess.run(["git", "add", "."], check=True)

        # 3. Commit with the provided message
        subprocess.run(["git", "commit", "-m", message], check=True)

        # 4. Push to the current branch
        subprocess.run(["git", "push"], check=True)

        print("Successfully updated requirements and pushed to Git!")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Usage
message = "removing seeding logic 3"
git_push(message)
