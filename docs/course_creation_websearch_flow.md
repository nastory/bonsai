This is roughly how the llm calls should be orchestrated for creating courses and content for Bonsai

## Course Creation
1. Course creation interview - user is interviewed to determine subject, scope, depth, etc., for the course they want
2. Course outline is generated - Modules and learning activity titles and plans are generated. No content generated yet, just the syllabus.
    - thumbnail generated, if applicable
3. User approves or suggests changes.
4. Compaction - Interview and syllabus are condensed to main points and saved as course context. Changes in course direction, future module generation, etc., will use this as a baseline memory for what the course is about

## Module generation
First module is generated as soon as syllabus is completed. Following, modules are generated as earlier ones are completed.
1. Look at upcoming module and learning activities
    - for each activity, create optimized search terms
2. Retrieval agent performs tavily searches for each activity, store search results in structured dictionary. No course content generation yet.
    - add toggle for "deep search," which uses the deep search functions in tavily.
3. Generate learning activities as cohesive chat history to ensure continuity between learning activities.
    - Generate one activity at a time, store as chat history -- prompt to create a lesson based on first tavily search, prompt to create a lesson that continues the previous and is based on second search results, and so on...
    - saved as structured course learning history, is built upon by subsequent modules; so each module builds on the last, and the lessons are cohesive and follow a logical flow.
    - Course learning history eventually indexed/embedded for search and question answering

## Course Extension and Branching
Works the same as generating modules, but creates a new course and continues from the course learning history of the base course.
For branching, it continues from a specific point in the course learning history and doesn't include hostory after that point.
