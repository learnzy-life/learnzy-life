import streamlit as st
import pandas as pd
import time

# Google Sheets CSV URL
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR4BK9IQmKNdiw3Gx_BLj_3O_uAKmt4SSEwmqzGldFu0DhMnKQ4QGOZZQ1AsY-6AbbHgAGjs5H_gIuV/pub?output=csv'

# Initialize session state
def init_session():
    required_states = {
        'authenticated': False,
        'test_started': False,
        'current_question': 0,
        'user_answers': {},
        'username': None,
        'start_time': None
    }
    for key, value in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# Load questions with exact column matching
@st.cache_data(ttl=3600)
def load_questions():
    try:
        df = pd.read_csv(SHEET_URL)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Verify required columns
        required_columns = [
            'Question ID', 'Question Text', 'Option A', 'Option B',
            'Option C', 'Option D', 'Correct Answer', 'Subject', 'Topic',
            'Sub- Topic', 'Difficulty Level', 'Question Type', 'Cognitive Level'
        ]
        
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
            return []
            
        return df[required_columns].to_dict(orient='records')
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        return []

questions = load_questions()

# Authentication
def authenticate():
    with st.form("auth"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if username == "user1" and password == "password1":
                st.session_state.authenticated = True
                st.session_state.username = username
            else:
                st.error("Invalid credentials")

# Analysis functions
def analyze_tag(tag_name):
    analysis = {}
    for q in questions:
        tag_value = q[tag_name]
        ans = st.session_state.user_answers.get(q['Question ID'], {})
        
        if tag_value not in analysis:
            analysis[tag_value] = {'total':0, 'correct':0, 'time':0}
        
        analysis[tag_value]['total'] += 1
        analysis[tag_value]['time'] += ans.get('time_taken',0)
        if ans.get('selected') == q['Correct Answer']:
            analysis[tag_value]['correct'] += 1
    
    for tag in analysis:
        stats = analysis[tag]
        stats['accuracy'] = (stats['correct']/stats['total'])*100
        stats['avg_time'] = stats['time']/stats['total']
    
    return analysis

def show_results():
    st.balloons()
    st.title("📊 Comprehensive Performance Report")
    
    # Basic metrics
    total_time = sum(ans['time_taken'] for ans in st.session_state.user_answers.values())
    topper_time = total_time * 0.7
    correct = sum(1 for ans in st.session_state.user_answers.values() 
                 if ans['selected'] == ans['correct'])
    accuracy = (correct / len(questions)) * 100

    # Time Analysis
    with st.expander("⏱ Time Management", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Your Time", f"{total_time:.1f}s")
        col2.metric("Topper Benchmark", f"{topper_time:.1f}s")
        col3.metric("Difference", f"{total_time-topper_time:.1f}s", 
                   delta="Over" if total_time > topper_time else "Under")
        
        # Time chart
        time_data = [{
            'Question': q['Question ID'],
            'Your Time': st.session_state.user_answers[q['Question ID']]['time_taken'],
            'Topper Time': st.session_state.user_answers[q['Question ID']]['time_taken'] * 0.7
        } for q in questions]
        st.line_chart(pd.DataFrame(time_data).set_index('Question'))

    # Subject/Topic Analysis
    with st.expander("📚 Subject/Topic Breakdown"):
        # Subject-wise
        st.subheader("Subject Performance")
        subject_stats = analyze_tag('Subject')
        for subject, stats in subject_stats.items():
            st.progress(stats['accuracy']/100)
            st.write(f"**{subject}**: {stats['accuracy']:.1f}% | Avg Time: {stats['avg_time']:.1f}s")
        
        # Sub-topic
        st.subheader("Sub-topic Analysis")
        subtopic_stats = analyze_tag('Sub- Topic')
        for subtopic, stats in subtopic_stats.items():
            col1, col2 = st.columns(2)
            col1.metric(subtopic, f"{stats['accuracy']:.1f}%")
            col2.metric("Avg Time", f"{stats['avg_time']:.1f}s")

    # Advanced Analysis
    with st.expander("🔍 Deep Insights"):
        tabs = st.tabs(["Difficulty", "Question Type", "Cognitive"])
        
        # Difficulty
        with tabs[0]:
            diff_stats = analyze_tag('Difficulty Level')
            for level in ['Easy', 'Medium', 'Hard']:
                if level in diff_stats:
                    st.write(f"**{level}**")
                    col1, col2 = st.columns(2)
                    col1.metric("Accuracy", f"{diff_stats[level]['accuracy']:.1f}%")
                    col2.metric("Avg Time", f"{diff_stats[level]['avg_time']:.1f}s")
        
        # Question Type
        with tabs[1]:
            type_stats = analyze_tag('Question Type')
            st.bar_chart(pd.DataFrame(type_stats).T['accuracy'])
        
        # Cognitive Level
        with tabs[2]:
            cog_stats = analyze_tag('Cognitive Level')
            for level in ['Remember', 'Understand', 'Apply', 'Analyze']:
                if level in cog_stats:
                    st.write(f"**{level}**")
                    st.progress(cog_stats[level]['accuracy']/100)

    # Recommendations
    st.header("🚀 Improvement Plan")
    
    # Weak subtopics
    weak_subtopics = [k for k,v in subtopic_stats.items() if v['accuracy'] < 70]
    if weak_subtopics:
        st.error(f"**Focus Subtopics:** {', '.join(weak_subtopics)}")
    
    # Difficulty
    weak_diff = [k for k,v in analyze_tag('Difficulty Level').items() if v['accuracy'] < 70]
    if weak_diff:
        st.warning(f"**Practice More:** {', '.join(weak_diff)} level questions")
    
    # Cognitive
    weak_cog = [k for k,v in cog_stats.items() if v['accuracy'] < 70]
    if weak_cog:
        st.info(f"**Develop Skills:** {', '.join(weak_cog)} level questions")

# Question Display
def display_question(q):
    st.subheader(f"Question {st.session_state.current_question + 1}")
    st.markdown(f"**{q['Question Text']}**")
    
    options = [q['Option A'], q['Option B'], q['Option C'], q['Option D']]
    answer = st.radio("Choose answer:", options, key=f"q{st.session_state.current_question}")
    
    if st.button("Next ➡️"):
        # Record response
        st.session_state.user_answers[q['Question ID']] = {
            'selected': chr(65 + options.index(answer)),
            'correct': q['Correct Answer'],
            'time_taken': time.time() - st.session_state.start_time
        }
        st.session_state.current_question += 1
        st.session_state.start_time = time.time()
        st.rerun()

# Main App
st.title("AI Mock Test Platform 🚀")

if not st.session_state.authenticated:
    authenticate()
else:
    if not questions:
        st.error("No questions loaded. Check data source!")
    elif not st.session_state.test_started:
        st.header(f"Welcome {st.session_state.username}!")
        st.write(f"Total Questions: {len(questions)}")
        if st.button("Start Test 🚀"):
            st.session_state.test_started = True
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        if st.session_state.current_question < len(questions):
            q = questions[st.session_state.current_question]
            display_question(q)
        else:
            show_results()
            if st.button("Retake Test 🔄"):
                st.session_state.clear()
                init_session()
                st.rerun()
