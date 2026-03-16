# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the secret number kept changing" or "the hints were backwards").

- The hints were flipped, when I put a high number it said go higher, and the vice versa for a low number
- Additionally, normal had a smaller range than hard, making the difficulties switched
- Another issue was that when a new game was started attemps was reset visually but did not actually change
---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

- I used Claude code as my AI tool
- One example of an AI suggestion that was correct was some of my tests were failing as they were expecting strings but the result was a tuple, and I was unable to catch that but the AI noticed quickly and gave advice on how to unpack tuples to make sure the test could read the result
- One suggestion that was somewhat misleading was the AI tried to change items that were irrelevant to the problems I was asking it to assist with, taking us off track. By making sure to read each suggestion and code edit, I made sure we did not make random changes we did not need
---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

- I decided if a bug was fixed first in the front end to make sure the game worked as intended, then in the back end using tests
- One test done manually was checking the labels for the results, and ensuring they displayed the correct text in the front end. It showed how the buggy code initially had the right ideas but carried them out with faulty logic
- AI helped me write the pytests as I was unfamiliar, it walked me through installing pytest and how it works in order to have a backend test for all the bugs

---

## 4. What did you learn about Streamlit and state?

- In your own words, explain why the secret number kept changing in the original app.
- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?
- What change did you make that finally gave the game a stable secret number?

- The code runs from top to bottom every time you interact with it in streamlit, thus causing the secret number to keep changing every time we ran it. 
- Streamlit is like a tool that runs code everytime you click it, just holding a very temporary session of your specific code. Session state is like a cheatsheet Streamlit uses to save important information before creasing a new temporary session of you code. 
- The change that fixed the code was assigning the secret number to the session state, allowing the Streamlit to track the number and remember it.
---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

- I want to keep using AI as a partner instead of a crutch, relying on it only to make sure I am not spending all my time writing code line by line, instead focusing on the bigger picture and having AI go through and complete the code quicker
- Next time I work with AI I will be sure to document everything closer, in order to make sure I am keeping track of what changes it makes
- This project made me realize how buggy AI code can be, and how important it is as the developer to keep a close eye on what changes the AI is making