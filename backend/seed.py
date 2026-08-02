"""Seed the database with example course data for local development.

Mirrors what used to be the frontend's Phase 0 fixtures (frontend/src/data/,
now removed since the frontend fetches real data instead), so the app has
something to look at while the real course-creation flow isn't built yet.

Run with: python seed.py
"""

from app import create_app
from app.extensions import db
from app.models import Activity, Course, Module, SourceMaterial


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
    course.source_materials = [
        SourceMaterial(
            id="src-1",
            file_name="Efficient-Memory-Coalescing-in-CUDA-Kernels.pdf",
            file_path="/data/source_materials/src-1.pdf",
        ),
    ]

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
        Activity(id="m1-a4", position=3, activity_type="assessment", title="Module 1 Assessment",
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
               learning_outcomes=["Implement scaled dot-product attention from scratch"]),
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
               learning_outcomes=["Implement a binary search tree"]),
        Module(id="dsa-module-3", position=2, title="Graphs",
               description="Graph representations, BFS/DFS, and shortest paths.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Implement Dijkstra's algorithm"]),
        Module(id="dsa-module-4", position=3, title="Sorting & Searching",
               description="Comparison sorts, divide-and-conquer, and binary search.",
               estimated_timeline="1 week", status="locked",
               learning_outcomes=["Compare sorting algorithms by time and space complexity"]),
        Module(id="dsa-module-5", position=4, title="Dynamic Programming Capstone",
               description="A capstone project solving a real optimization problem with DP.",
               estimated_timeline="2 weeks", status="locked",
               learning_outcomes=["Recognize and solve overlapping-subproblem problems"]),
    ]
    return course


if __name__ == "__main__":
    seed()
