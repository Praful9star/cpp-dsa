"""
tools/dsa.py — C++ / DSA tutor, problem of the day, quiz mode.

"Explain binary search"
"What is a linked list"
"Give me a DSA problem"
"Quiz me on C++"
"What's today's problem"
"""
import random
import datetime
import sqlite3
import os
import config

DB_PATH = config.DB_PATH

DSA_PROBLEMS = [
    {"title": "Two Sum", "difficulty": "Easy",
     "desc": "Given an array of integers and a target, return indices of two numbers that add up to target. Think hash map for O(n) solution."},
    {"title": "Reverse a Linked List", "difficulty": "Easy",
     "desc": "Reverse a singly linked list. Use three pointers: prev, current, next. Iterate and flip links one by one."},
    {"title": "Binary Search", "difficulty": "Easy",
     "desc": "Search a sorted array in O(log n). Key: set low=0, high=n-1, mid=(low+high)/2. Halve the search space each step."},
    {"title": "Valid Parentheses", "difficulty": "Easy",
     "desc": "Check if brackets are balanced. Use a stack — push opening brackets, pop on closing. Stack should be empty at end."},
    {"title": "Maximum Subarray (Kadane's)", "difficulty": "Easy",
     "desc": "Find the contiguous subarray with the largest sum. Track current_sum and max_sum. Reset current_sum to 0 when it goes negative."},
    {"title": "Merge Two Sorted Arrays", "difficulty": "Easy",
     "desc": "Merge two sorted arrays into one sorted array. Use two pointers, compare and pick smaller element each time."},
    {"title": "Find Duplicates in Array", "difficulty": "Easy",
     "desc": "Find duplicates in an array. Use an unordered_set in C++ — insert each element, if already present it's a duplicate."},
    {"title": "Level Order Traversal of Tree", "difficulty": "Medium",
     "desc": "BFS on a binary tree. Use a queue — enqueue root, then for each node, process it and enqueue left and right children."},
    {"title": "LRU Cache", "difficulty": "Medium",
     "desc": "Design a Least Recently Used cache. Use a doubly linked list plus a hash map. Map stores key-to-node, list maintains order."},
    {"title": "Number of Islands", "difficulty": "Medium",
     "desc": "Count connected groups of 1s in a 2D grid. Use DFS or BFS from each unvisited 1, mark visited cells as 0."},
    {"title": "Longest Common Subsequence", "difficulty": "Medium",
     "desc": "Find the longest subsequence common to two strings. Classic DP — fill a 2D table where dp[i][j] = LCS of first i and j chars."},
    {"title": "Detect Cycle in Linked List", "difficulty": "Medium",
     "desc": "Floyd's algorithm: use slow and fast pointers. If they ever meet, there's a cycle."},
    {"title": "Binary Tree Height", "difficulty": "Easy",
     "desc": "Height = 1 + max(height of left subtree, height of right subtree). Base case: null node returns 0."},
    {"title": "Quick Sort", "difficulty": "Medium",
     "desc": "Pick a pivot, partition array so left side < pivot < right side, recursively sort both sides. Average O(n log n)."},
    {"title": "Dijkstra's Shortest Path", "difficulty": "Hard",
     "desc": "Find shortest path in a weighted graph. Use a min-heap priority queue. Greedily pick the unvisited node with smallest distance."},
    {"title": "Trie Insert and Search", "difficulty": "Medium",
     "desc": "A trie stores strings character by character in a tree. Each node has 26 children (one per letter). Insert walks and creates nodes."},
    {"title": "Stack using Queues", "difficulty": "Easy",
     "desc": "Implement a stack using two queues. On push, enqueue to q1. On pop, move all but last element to q2, dequeue last, swap q1 and q2."},
    {"title": "Rotate Array by K", "difficulty": "Easy",
     "desc": "Rotate an array right by k steps. Trick: reverse the whole array, then reverse first k, then reverse remaining."},
    {"title": "Climbing Stairs", "difficulty": "Easy",
     "desc": "Count ways to climb n stairs taking 1 or 2 steps. It's Fibonacci! dp[i] = dp[i-1] + dp[i-2]."},
    {"title": "Anagram Check", "difficulty": "Easy",
     "desc": "Check if two strings are anagrams. Sort both and compare, or use a frequency map of 26 characters."},
]

CPP_QUIZ = [
    {"q": "What is the difference between a pointer and a reference in C++?",
     "a": "A pointer can be null and can be reassigned to point to different objects. A reference must be initialized and always refers to the same object — it's basically an alias."},
    {"q": "What does 'const' do in C++?",
     "a": "It makes a variable or parameter read-only. A const variable can't be changed after initialization. It's also used in function signatures to prevent modification of parameters."},
    {"q": "What is the difference between stack and heap memory?",
     "a": "Stack is fast, automatically managed, and for local variables — but limited in size. Heap is for dynamic memory allocated with 'new', you manage it manually with delete, and it's much larger."},
    {"q": "What is a virtual function?",
     "a": "A virtual function enables runtime polymorphism. When a base class pointer calls a virtual function, it calls the derived class's version. Declared with the 'virtual' keyword."},
    {"q": "What is the difference between struct and class in C++?",
     "a": "Technically just default access — struct members are public by default, class members are private. Otherwise they're identical in C++."},
    {"q": "What is a destructor?",
     "a": "A special method called automatically when an object goes out of scope or is deleted. Used to free resources. Named like the class but with a tilde prefix — like ~MyClass."},
    {"q": "What is operator overloading?",
     "a": "Defining custom behavior for operators like +, -, ==, << for your own classes. For example, you can make two Vector objects add with the + operator."},
    {"q": "What is the STL?",
     "a": "The Standard Template Library — a set of ready-made data structures and algorithms in C++. Includes vector, map, set, queue, stack, sort, find, and much more."},
    {"q": "What is a template in C++?",
     "a": "A way to write generic code that works with any data type. Instead of writing separate functions for int, float, etc., you write one template function. Like a blueprint."},
    {"q": "What is Big O notation?",
     "a": "A way to describe how an algorithm's time or space grows as input size grows. O(1) is constant, O(n) is linear, O(n squared) is quadratic, O(log n) is very fast like binary search."},
]

_quiz_session: dict = {"active": False, "index": 0, "score": 0, "total": 0}


def problem_of_the_day() -> str:
    """Return a deterministic daily problem based on the date."""
    day_index = datetime.date.today().toordinal() % len(DSA_PROBLEMS)
    p = DSA_PROBLEMS[day_index]
    _save_problem_seen(p["title"])
    return (
        f"Today's DSA problem: {p['title']} — {p['difficulty']}. "
        f"{p['desc']} Want me to go deeper on any part of this?"
    )


def random_problem() -> str:
    """Return a random unseen problem, or random if all seen."""
    seen = _get_seen_problems()
    unseen = [p for p in DSA_PROBLEMS if p["title"] not in seen]
    pool = unseen if unseen else DSA_PROBLEMS
    p = random.choice(pool)
    _save_problem_seen(p["title"])
    return (
        f"Here's a {p['difficulty']} problem: {p['title']}. "
        f"{p['desc']}"
    )


def start_quiz() -> str:
    """Start a C++ quiz session."""
    global _quiz_session
    questions = CPP_QUIZ.copy()
    random.shuffle(questions)
    _quiz_session = {
        "active": True,
        "questions": questions,
        "index": 0,
        "score": 0,
        "total": min(5, len(questions)),
    }
    first = questions[0]
    return f"Quiz time! Question 1 of {_quiz_session['total']}: {first['q']}"


def next_quiz_question(user_answer: str = "") -> str:
    """Advance quiz and give answer + next question."""
    global _quiz_session
    if not _quiz_session.get("active"):
        return start_quiz()

    idx = _quiz_session["index"]
    questions = _quiz_session["questions"]
    current = questions[idx]

    response = f"Answer: {current['a']} "
    _quiz_session["index"] += 1
    _quiz_session["score"] += 1

    if _quiz_session["index"] >= _quiz_session["total"]:
        _quiz_session["active"] = False
        return response + f"Quiz done! You went through {_quiz_session['total']} questions. Great session, Praful!"

    next_q = questions[_quiz_session["index"]]
    qnum   = _quiz_session["index"] + 1
    return response + f"Question {qnum}: {next_q['q']}"


def explain_concept(query: str) -> str:
    """Return a short explanation of a DSA/C++ concept."""
    # This is passed to Groq with a special prompt in brain.py
    return f"EXPLAIN_DSA:{query}"


# ── SQLite helpers ─────────────────────────────────────────────────────────────

def _save_problem_seen(title: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dsa_seen (
                title TEXT PRIMARY KEY, seen_on TEXT
            )""")
        conn.execute("INSERT OR IGNORE INTO dsa_seen VALUES (?, date('now'))", (title,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _get_seen_problems() -> set:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS dsa_seen (title TEXT PRIMARY KEY, seen_on TEXT)")
        rows = conn.execute("SELECT title FROM dsa_seen").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except Exception:
        return set()
