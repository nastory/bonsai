# Bonsai
An open-source flexible AI learning application by Nigel Story
(I wrote all this myself, I just like em dashes)

## Motivation
I love continuous learning, but I get tired of having to search through sites like Udemy or Coursera looking for courses, not finding exactly what I need, and then paying for a course that only loosely lines up with what I actually want to learn.

While laying in bed after searching for a good course on practical GPU programming for ML/AI engineers and not having any luck, I decided to ask Claude for advice. Is GPU programming worth learning? Where would it be best for an ML engineer to focus? What technology and programming languages would be involved? And finally, can you draft a course outline for me?

The outline drafted was very good -- it had a great structured approach with modules, timelines, practicum, and even a capstone project; but again, only the outline. The question then became how would I have Claude actually go about creating this course for me in an engaging, practical, and motivating way. If I could figure that out, I could have it teach me anything.

Recently, I've been on a bonsai kick on TikTok. The meditative patience that goes into creating and maintaining these seemingly ancient trees in miniature is fascinating to me: wiring shoots and cutting limbs, cleaning roots, repotting -- all with patient goal of creating something beautiful. That's the experience I want from this learning platform: a self-guided, self-built program of learning where the student has the ability to reshape the curriculum as they go through AI. The fact that Bonsai has "AI" in its name is just a fun coincidence.

## Basic Rough Idea
I want to start off as basic as possible just to get something working, so here's what I have in mind:

### 1. Bonsai front-end
The front-end user experience would look something like a Coursera/Udemy interface, but instead of selecting courses to take, the user would create a course (course creation to be addressed later). The courses would have modules, assessments, excercises, etc., that would help the learner retain the materials.

The user could create courses and navigate between them, navigate between lessons and modules, etc, all the expected navigation to participate in the learning activities. Since this would all be open-source and locally hosted by the learner, they can create as many courses as they want and as deep a learning experience as they want.

### 2. Course Creation
Here's where things could start to get complex.

The easy way to implement this, and probably the best for a proof-of-concept, would be to create a `bonsai` skill for Claude where the user tells Claude what they want to learn, Claude prompts them for information about their existing experience, how deep they want to go, if there are focus areas they want to zoom in on, etc., and then it would create a structured `course_outline`, maybe in JSON or markdown, that the user would drop into the front-end to create the course. Then the modules would be created as you go, according to the outline, and taking in user feedback if the user wants to alter course or change the existing outline. But then I guess if those steps are happening in-app via API call to whatever LLM, then the initial course creation could also happen that way. 

### 3. Learning Materials
The course outline would include course title and description, prerequisites, estimated timeline, and then list the modules. Modules would include titles, descriptions, timelines, learning activities, and learning outcomes. The learning activities might be guided readings, articles, youtube videos, assessments, practical excercises.

The materials would be sourced from the web: publicly available information, articles, videos, etc. For articles and text data, it would be read in by the LLM and synthesized into guided learning meterials. It would be vital for these resources to be vetted and cited, with inline links available. Videos would need to be embedded and viewable from within the app.

Dependencies should be mapped so that a logical learning flow is possible and there are no holes in the curriculum that might confuse or misguide the learners.

### 4. Restrictions & Disclaimers
Most of these restrictions should come along through the LLM itself, but Bonsai would need to enforce them as well:
1. Nothing illegal should EVER be taught, referenced, recommended, or otherwise encouraged -- drug manufacturing, harm to self or others, bomb making, racism/hate, none of that is allowed.
2. Medical or Legal learning MUST come with strong disclaimers that this in no way qualifies or licenses the learner to practice or advise. This does not qualify in any way as training in those fields.
3. Learners might be interested in esoteric topics, like conspiracy theories, magic, alternative medicine, etc. Bonsai should be clear when discussing these topics whenever they contradict scientific concensus, official statements or records, etc.
4. Bonsai should take neutral stances when discussing religion and politics.
5. Bonsai is not accredited in any way. You build your own curriculum, and so the knowledge is the only thing you can get from it. It's not a degree; it's not a certification; it's simply self-improvement.
6. The learning materials are compiled and, in some cases, synthesized by AI. Bonsai makes absolutely no guarantees of the correctness of the information in its courses and learning materials. Where available, learners should refer to source materials for the most accurate information.


### 5. Rough Idea of User Experience
This is how I would want my experience to be as a Bonsai user wanting to learn about GPU programming:

I open up Bonsai and hit "Create a New Course." Bonsai asks me what I want to learn about. I say I want to learn about GPU programming. Bonsai follows up with questions about my existing experience, why I want to learn about GPUs, how I want to be able to use them, if I have any related knowledge, if there are specific areas I want to focus on etc. The questions would be generated on the fly according to the topic and my answers; one question per screen with a text box for me to type answers. After at most 10 questions, Bonsai generates the course outline and asks me how it looks. I can ask for it to be revised and provide feedback, or I can "Start Learning." Bonsai creates the course and generates the first module's contents. I do the learning activities. Modules are generated as I work through the course according to the course outline. At the end of each module, Bonsai asks how it's going -- I have the ability to say "I'd like to change directions..." and alter the remaining modules to better fit the direction I have in mind.  I could also change the module I'm currently working on, but the newly created module would not have my existing progress. When I complete a course, I get a "Congratulations" and my completed courses are tallied. Courses, lessons, topics, etc. are indexed so I can search for them later.

I can also select a completed course and say "keep going" or "dive deeper" to create a new course that dives deeper into the topic or goes more advanced. I could also "branch off" into a related or tangential topic.

