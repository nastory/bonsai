"""Seed the database with example course data for local development.

Mirrors what used to be the frontend's Phase 0 fixtures (frontend/src/data/,
now removed since the frontend fetches real data instead), so the app has
something to look at while the real course-creation flow isn't built yet.

Run with: python seed.py
"""

from app import create_app
from app.extensions import db
from app.models import Activity, Course, Module


def seed() -> None:
    """Insert the example courses if the database is empty."""
    app = create_app()
    with app.app_context():
        if db.session.execute(db.select(Course)).first() is not None:
            print("Database already has courses; skipping seed.")
            return

        db.session.add(_gpu_programming_course())
        db.session.add(_deep_learning_foundations_course())
        db.session.add(_data_structures_course())
        db.session.commit()
        print("Seeded 3 courses.")


def _gpu_programming_course() -> Course:
    course = Course(
        id="gpu-programming",
        title="GPU Programming for ML Engineers",
        description=(
            "A practical path through GPU architecture, memory, and parallel programming "
            "patterns, aimed at ML engineers who want to understand what their training "
            "jobs are actually doing on the hardware."
        ),
        prerequisites=["Comfortable with Python", "Basic linear algebra"],
        estimated_timeline="6 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
    )
    # No SourceMaterial fixture here: real ingestion (see
    # app/services/document_extraction.py) needs a real extracted-text file
    # on disk to back one, which this demo seed data never had — a fake
    # placeholder would crash module generation's document-grounded branch
    # the moment it tried to read a nonexistent file.

    module_1 = Module(
        id="module-1",
        position=0,
        title="GPU Architecture Fundamentals",
        description="What a GPU actually is, and why it looks nothing like a CPU.",
        estimated_timeline="1 week",
        status="completed",
        learning_outcomes=[
            "Explain the difference between latency-optimized and throughput-optimized processors",
            "Describe the SIMT execution model",
        ],
    )
    module_1.activities = [
        Activity(id="m1-a1", position=0, activity_type="reading", title="What Is a GPU, Really?",
                  status="completed", estimated_minutes=15),
        Activity(id="m1-a2", position=1, activity_type="reading", title="SIMT: Single Instruction, Multiple Threads",
                  status="completed", estimated_minutes=20),
        Activity(id="m1-a3", position=2, activity_type="discussion", title="Comparing CPU and GPU Design",
                  status="completed", estimated_minutes=10),
        Activity(id="m1-a4", position=3, activity_type="quiz", title="Module 1 Check",
                  status="completed", estimated_minutes=10),
    ]

    module_2 = Module(
        id="module-2",
        position=1,
        title="Memory Hierarchy",
        description="The memory types available on a GPU, their trade-offs, and how to use them well.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=[
            "Name the GPU memory tiers from fastest to slowest",
            "Explain why register and shared memory usage affects occupancy",
        ],
    )
    # Only these 3: a module's activities are generated together in one call
    # (see module_generation.py), so there's no such thing as some of a
    # generated module's activities existing while others are still locked
    # pending completion order. This module simply hasn't had the rest of
    # its activities generated yet.
    module_2.activities = [
        Activity(id="m2-a1", position=0, activity_type="reading", title="GPU Memory Overview",
                  status="completed", estimated_minutes=12),
        Activity(id="m2-a2", position=1, activity_type="reading", title="Latency vs. Bandwidth",
                  status="completed", estimated_minutes=15),
        Activity(id="m2-a3", position=2, activity_type="reading", title="Memory Hierarchy",
                  status="available", estimated_minutes=20),
    ]

    module_3 = Module(
        id="module-3",
        position=2,
        title="Kernels & Parallel Patterns",
        description="Writing and launching kernels, and the parallel patterns (map, reduce, scan) that show up everywhere.",
        estimated_timeline="2 weeks",
        status="locked",
        learning_outcomes=["Write and launch a basic CUDA kernel", "Implement a parallel reduction"],
        activity_plan=[
            {"type": "reading", "title": "Writing Your First Kernel", "plan": "Kernel syntax and launch configuration."},
            {"type": "reading", "title": "Parallel Patterns: Map, Reduce, Scan", "plan": "The three patterns and when to use each."},
            {"type": "project", "title": "Implement a Parallel Reduction", "plan": "Hands-on reduction kernel."},
            {"type": "quiz", "title": "Module 3 Check", "plan": "Quiz on kernels and parallel patterns."},
        ],
    )

    module_4 = Module(
        id="module-4",
        position=3,
        title="Optimization & Profiling Capstone",
        description="A capstone project profiling and optimizing a real kernel using the tools and concepts from the course.",
        estimated_timeline="2 weeks",
        status="locked",
        learning_outcomes=[
            "Use a profiler to identify a kernel's bottleneck",
            "Apply at least two optimization techniques to improve throughput",
        ],
        activity_plan=[
            {"type": "reading", "title": "Profiling Tools Overview", "plan": "Introduce common GPU profiling tools."},
            {"type": "capstone", "title": "Profile and Optimize a Kernel", "plan": "Capstone: profile, optimize, and report gains."},
            {"type": "assessment", "title": "Course Assessment", "plan": "Comprehensive check across the whole course."},
        ],
    )

    course.modules = [module_1, module_2, module_3, module_4]
    return course


def _deep_learning_foundations_course() -> Course:
    course = Course(
        id="deep-learning-foundations",
        title="Deep Learning Foundations",
        description="Core concepts behind modern neural networks, from backpropagation to attention.",
        prerequisites=["Basic linear algebra", "Basic Python"],
        estimated_timeline="5 weeks",
        thumbnail_url="from-violet-950 to-indigo-900",
    )
    course.modules = [
        Module(id="dl-module-1", position=0, title="Neural Network Basics",
               description="Perceptrons, activation functions, and backpropagation.",
               estimated_timeline="2 weeks", status="completed",
               learning_outcomes=["Derive backpropagation for a small network"]),
        Module(id="dl-module-2", position=1, title="Convolutional Networks",
               description="Convolutions, pooling, and image classification.",
               estimated_timeline="1 week", status="in_progress",
               learning_outcomes=["Explain why convolutions share parameters across an image"]),
        Module(id="dl-module-3", position=2, title="Attention & Transformers",
               description="Self-attention and the transformer architecture, capstone project included.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Implement scaled dot-product attention from scratch"],
               activity_plan=[
                   {"type": "reading", "title": "Self-Attention Explained", "plan": "Queries, keys, and values."},
                   {"type": "reading", "title": "The Transformer Architecture", "plan": "Encoder/decoder stacks and positional encoding."},
                   {"type": "capstone", "title": "Implement Scaled Dot-Product Attention", "plan": "Capstone: build attention from scratch."},
                   {"type": "assessment", "title": "Course Assessment", "plan": "Comprehensive check across the whole course."},
               ]),
    ]
    return course


def _data_structures_course() -> Course:
    course = Course(
        id="data-structures-algorithms",
        title="Data Structures & Algorithms",
        description="A ground-up tour of the data structures and algorithms every engineer eventually needs.",
        prerequisites=["Comfortable writing basic programs"],
        estimated_timeline="8 weeks",
        thumbnail_url="from-stone-500 to-stone-700",
    )
    course.modules = [
        Module(id="dsa-module-1", position=0, title="Arrays, Lists & Complexity",
               description="Big-O notation, arrays vs. linked lists.",
               estimated_timeline="1 week", status="in_progress",
               learning_outcomes=["Analyze the time complexity of common operations"]),
        Module(id="dsa-module-2", position=1, title="Stacks, Queues & Trees",
               description="Core structures and their traversal patterns.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Implement a binary search tree"],
               activity_plan=[
                   {"type": "reading", "title": "Stacks & Queues", "plan": "LIFO/FIFO structures and their use cases."},
                   {"type": "reading", "title": "Trees & Traversal", "plan": "Binary trees and traversal orders."},
                   {"type": "project", "title": "Implement a Binary Search Tree", "plan": "Build and traverse a BST."},
                   {"type": "quiz", "title": "Module 2 Check", "plan": "Quiz on stacks, queues, and trees."},
               ]),
        Module(id="dsa-module-3", position=2, title="Graphs",
               description="Graph representations, BFS/DFS, and shortest paths.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Implement Dijkstra's algorithm"],
               activity_plan=[
                   {"type": "reading", "title": "Graph Representations", "plan": "Adjacency lists vs. matrices."},
                   {"type": "reading", "title": "BFS, DFS & Shortest Paths", "plan": "Traversal algorithms and Dijkstra's algorithm."},
                   {"type": "project", "title": "Implement Dijkstra's Algorithm", "plan": "Build a shortest-path solver."},
                   {"type": "quiz", "title": "Module 3 Check", "plan": "Quiz on graph algorithms."},
               ]),
        Module(id="dsa-module-4", position=3, title="Sorting & Searching",
               description="Comparison sorts, divide-and-conquer, and binary search.",
               estimated_timeline="1 week", status="locked",
               learning_outcomes=["Compare sorting algorithms by time and space complexity"],
               activity_plan=[
                   {"type": "reading", "title": "Comparison Sorts", "plan": "Merge sort, quicksort, and their complexity."},
                   {"type": "reading", "title": "Binary Search", "plan": "Divide-and-conquer search on sorted data."},
                   {"type": "quiz", "title": "Module 4 Check", "plan": "Quiz on sorting and searching."},
               ]),
        Module(id="dsa-module-5", position=4, title="Dynamic Programming Capstone",
               description="A capstone project solving a real optimization problem with DP.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Recognize and solve overlapping-subproblem problems"],
               activity_plan=[
                   {"type": "reading", "title": "Dynamic Programming Fundamentals", "plan": "Overlapping subproblems and memoization."},
                   {"type": "capstone", "title": "Solve an Optimization Problem with DP", "plan": "Capstone: apply DP to a real problem."},
                   {"type": "assessment", "title": "Course Assessment", "plan": "Comprehensive check across the whole course."},
               ]),
    ]
    return course


if __name__ == "__main__":
    seed()
