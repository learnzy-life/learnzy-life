import streamlit as st
import pandas as pd
import time
import csv
import os

# Configuration
GSHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR4BK9IQmKNdiw3Gx_BLj_3O_uAKmt4SSEwmqzGldFu0DhMnKQ4QGOZZQ1AsY-6AbbHgAGjs5H_gIuV/pubhtml?gid=0&single=true'
USERS_DB = {'user1': 'password1', 'user2': 'password2'}

# Initialize session state
def init_session():
    required_states = {
        'authenticated': False,
        'test_started': False,
        'current_question': 0,
        'user_answers': {},
        'question_start_time': time.time(),
        'username': None
    }
    for key, value in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# Data loading
@st.cache_data
def load_questions():
    try:
        df = pd.read_csv(GSHEET_URL)
        required_columns = ['Question ID', 'Question Text', 'Option A', 'Option B',
                           'Option C', 'Option D', 'Correct Answer', 'Subject', 'Topic',
                           'Sub- Topic', 'Difficulty Level', 'Question Type', 'Cognitive Level']
        return df[required_columns].to_dict(orient='records')
    except Exception as e:
        st.error(f"Error loading questions: {str(e)}")
        return []

questions = load_questions()

# Helper functions
def get_topper_time(user_time):
    return user_time * 0.7

def analyze_by_tag(tag_name):
    analysis = {}
    for q in questions:
        tag_value = q[tag_name]
        ans = st.session_state.user_answers.get(q['Question ID'], {})
        
        if tag_value not in analysis:
            analysis[tag_value] = {'total': 0, 'correct': 0, 'time': 0}
        
        analysis[tag_value]['total'] += 1
        analysis[tag_value]['time'] += ans.get('time_taken', 0)
        if ans.get('selected') == q['Correct Answer']:
            analysis[tag_value]['correct'] += 1
    
    for tag in analysis:
        stats = analysis[tag]
        stats['accuracy'] = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
        stats['avg_time'] = stats['time'] / stats['total'] if stats['total'] > 0 else 0
    
    return analysis

def get_video_suggestions(topic):
    videos = {
        'Kinematics': 'https://youtu.be/example1',
        'Thermodynamics': 'https://youtu.be/example2',
        'Organic Chemistry': 'https://youtu.be/example3'
    }
    return videos.get(topic, "#")

# Authentication
def authenticate():
    with st.form("auth"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if USERS_DB.get(username) == password:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")

# Test interface
def display_question(q):
    st.subheader(f"Question {st.session_state.current_question + 1} of {len(questions)}")
    st.markdown(f"**{q['Question Text']}**")
    
    options = [q['Option A'], q['Option B'], q['Option C'], q['Option D']]
    answer = st.radio("Choose your answer:", options, key=f"q{st.session_state.current_question}")
    
    if st.button("Next ➡️"):
        process_answer(q, answer)
        st.session_state.current_question += 1
        st.session_state.question_start_time = time.time()
        st.rerun()

def process_answer(q, answer):
    options = [q['Option A'], q['Option B'], q['Option C'], q['Option D']]
    selected_option = chr(65 + options.index(answer))
    
    st.session_state.user_answers[q['Question ID']] = {
        'selected': selected_option,
        'correct': q['Correct Answer'],
        'time_taken': time.time() - st.session_state.question_start_time
    }

# Results display
def show_results():
    st.balloons()
    st.title("📊 Comprehensive Analysis Report")
    
    # Basic metrics
    total_time = sum(a['time_taken'] for a in st.session_state.user_answers.values())
    topper_time = total_time * 0.7
    correct = sum(1 for a in st.session_state.user_answers.values() if a['selected'] == a['correct'])
    accuracy = (correct / len(questions)) * 100

    # Time analysis
    with st.expander("⏱ Time Performance", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Your Total Time", f"{total_time:.1f}s")
        col2.metric("Topper's Benchmark", f"{topper_time:.1f}s")
        col3.metric("Difference", f"{total_time - topper_time:.1f}s", 
                   delta=f"{'Over' if total_time > topper_time else 'Under'} Time")

    # Subject/Topic analysis
    with st.expander("📚 Subject & Topic Breakdown"):
        st.subheader("By Subject")
        subject_stats = analyze_by_tag('Subject')
        for subj, stats in subject_stats.items():
            st.progress(stats['accuracy']/100)
            st.write(f"**{subj}**: {stats['accuracy']:.1f}% | Avg Time: {stats['avg_time']:.1f}s")
        
        st.subheader("By Topic")
        topic_stats = analyze_by_tag('Topic')
        for topic, stats in topic_stats.items():
            cols = st.columns([1, 2, 2])
            cols[0].write(f"**{topic}**")
            cols[1].metric("Accuracy", f"{stats['accuracy']:.1f}%")
            cols[2].metric("Avg Time", f"{stats['avg_time']:.1f}s")

    # Advanced tag analysis
    with st.expander("🔍 Advanced Analysis"):
        tabs = st.tabs(["Difficulty", "Question Type", "Cognitive Level", "Sub-Topic"])
        
        with tabs[0]:  # Difficulty
            diff_stats = analyze_by_tag('Difficulty Level')
            for level in ['Easy', 'Medium', 'Hard']:
                if level in diff_stats:
                    stats = diff_stats[level]
                    st.write(f"**{level}**")
                    st.progress(stats['accuracy']/100)
                    st.caption(f"{stats['correct']}/{stats['total']} | Avg Time: {stats['avg_time']:.1f}s")
        
        with tabs[1]:  # Question Type
            type_stats = analyze_by_tag('Question Type')
            for q_type, stats in type_stats.items():
                st.metric(q_type, f"{stats['accuracy']:.1f}%", 
                         delta=f"Avg Time: {stats['avg_time']:.1f}s")
        
        with tabs[2]:  # Cognitive Level
            cog_stats = analyze_by_tag('Cognitive Level')
            df = pd.DataFrame.from_dict(cog_stats, orient='index')
            st.bar_chart(df['accuracy'])
        
        with tabs[3]:  # Sub-Topic
            subtopic_stats = analyze_by_tag('Sub- Topic')
            for subtopic, stats in subtopic_stats.items():
                cols = st.columns([2, 1, 1])
                cols[0].write(f"**{subtopic}**")
                cols[1].write(f"{stats['accuracy']:.1f}%")
                cols[2].write(f"{stats['avg_time']:.1f}s")

    # Recommendations
    st.header("🚀 Personalized Improvement Plan")
    
    # Weak areas
    weak_topics = [k for k,v in topic_stats.items() if v['accuracy'] < 70]
    if weak_topics:
        st.error(f"**Focus Topics:** {', '.join(weak_topics)}")
        for topic in weak_topics:
            st.write(f"- [Study {topic}]({get_video_suggestions(topic)})")
    
    # Difficulty recommendations
    diff_stats = analyze_by_tag('Difficulty Level')
    weak_diff = [k for k,v in diff_stats.items() if v['accuracy'] < 70]
    if weak_diff:
        st.warning(f"**Practice Difficulty Levels:** {', '.join(weak_diff)}")
    
    # Question type recommendations
    type_stats = analyze_by_tag('Question Type')
    weak_types = [k for k,v in type_stats.items() if v['accuracy'] < 70]
    if weak_types:
        st.info(f"**Improve Question Types:** {', '.join(weak_types)}")

    # Retake option
    if st.button("🔄 Retake Test"):
        st.session_state.clear()
        st.rerun()

# Main app flow
st.title("Smart Mock Test Platform 🚀")

if not questions:
    st.error("Failed to load questions. Please check the data source.")
elif not st.session_state.authenticated:
    authenticate()
else:
    if not st.session_state.test_started:
        st.write(f"Welcome {st.session_state.username}!")
        st.write(f"Total Questions: {len(questions)}")
        if st.button("Start Test 🚀"):
            st.session_state.test_started = True
            st.rerun()
    else:
        if st.session_state.current_question < len(questions):
            q = questions[st.session_state.current_question]
            display_question(q)
        else:
            show_results()
