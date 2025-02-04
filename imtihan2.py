import streamlit as st
import pandas as pd
import time

# Google Sheets CSV URL
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR4BK9IQmKNdiw3Gx_BLj_3O_uAKmt4SSEwmqzGldFu0DhMnKQ4QGOZZQ1AsY-6AbbHgAGjs5H_gIuV/pub?output=csv'

# Session state management
def init_session():
    required_states = {
        'authenticated': False,
        'test_started': False,
        'current_question': 0,
        'user_answers': {},
        'username': None,
        'start_time': None,
        'questions': []
    }
    for key, value in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# Data loading with validation
@st.cache_data(ttl=3600)
def load_valid_questions():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip()
        
        valid_questions = []
        required_columns = [
            'Question ID', 'Question Text', 'Option A', 'Option B',
            'Option C', 'Option D', 'Correct Answer', 'Subject', 'Topic',
            'Sub- Topic', 'Difficulty Level', 'Question Type', 'Cognitive Level'
        ]
        
        # Validate columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {', '.join(missing_cols)}")
            return []
        
        # Validate each question
        for _, row in df.iterrows():
            options = [
                str(row['Option A']).strip(),
                str(row['Option B']).strip(),
                str(row['Option C']).strip(),
                str(row['Option D']).strip()
            ]
            
            # Check for valid question structure
            if (all(options) and len(options) == 4 and 
                row['Correct Answer'].strip().upper() in ['A', 'B', 'C', 'D']):
                valid_questions.append(row.to_dict())
        
        if len(valid_questions) < len(df):
            st.warning(f"Skipped {len(df)-len(valid_questions)} invalid/malformed questions")
        
        return valid_questions
        
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        return []

# Authentication
def authenticate():
    with st.form("auth"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if username == "user1" and password == "password1":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.questions = load_valid_questions()
            else:
                st.error("Invalid credentials")

# Analysis functions
def analyze_tag(tag_name):
    analysis = {}
    for q in st.session_state.questions:
        tag_value = q.get(tag_name, 'N/A')
        ans = st.session_state.user_answers.get(q['Question ID'], {})
        
        if tag_value not in analysis:
            analysis[tag_value] = {'total':0, 'correct':0, 'time':0}
        
        analysis[tag_value]['total'] += 1
        analysis[tag_value]['time'] += ans.get('time_taken', 0)
        if ans.get('selected') == q['Correct Answer'].strip().upper():
            analysis[tag_value]['correct'] += 1
    
    for tag in analysis:
        stats = analysis[tag]
        stats['accuracy'] = (stats['correct']/stats['total'])*100 if stats['total'] > 0 else 0
        stats['avg_time'] = stats['time']/stats['total'] if stats['total'] > 0 else 0
    
    return analysis

# Results display
def show_results():
    st.balloons()
    st.title("📊 Comprehensive Analysis Report")
    
    # Basic metrics
    total_time = sum(ans['time_taken'] for ans in st.session_state.user_answers.values())
    topper_time = total_time * 0.7
    correct = sum(1 for ans in st.session_state.user_answers.values() 
                 if ans['selected'] == ans['correct'])
    accuracy = (correct / len(st.session_state.questions)) * 100 if st.session_state.questions else 0

    # Time Analysis
    with st.expander("⏱ Time Management", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Your Time", f"{total_time:.1f}s")
        col2.metric("Topper Benchmark", f"{topper_time:.1f}s")
        col3.metric("Difference", f"{total_time-topper_time:.1f}s", 
                   delta="Over" if total_time > topper_time else "Under")
        
        time_data = pd.DataFrame([
            {'Question': q['Question ID'], 
             'Your Time': st.session_state.user_answers[q['Question ID']]['time_taken'],
             'Topper Time': st.session_state.user_answers[q['Question ID']]['time_taken'] * 0.7}
            for q in st.session_state.questions
        ])
        st.line_chart(time_data.set_index('Question'))

    # Subject/Topic Analysis
    with st.expander("📚 Subject/Topic Breakdown"):
        st.subheader("Subject Performance")
        subject_stats = analyze_tag('Subject')
        for subject, stats in subject_stats.items():
            st.progress(stats['accuracy']/100)
            st.write(f"**{subject}**: {stats['accuracy']:.1f}% | Avg Time: {stats['avg_time']:.1f}s")
        
        st.subheader("Sub-topic Analysis")
        subtopic_stats = analyze_tag('Sub- Topic')
        for subtopic, stats in subtopic_stats.items():
            col1, col2 = st.columns(2)
            col1.metric(subtopic, f"{stats['accuracy']:.1f}%")
            col2.metric("Avg Time", f"{stats['avg_time']:.1f}s")

    # Advanced Analysis
    with st.expander("🔍 Deep Insights"):
        tabs = st.tabs(["Difficulty", "Question Type", "Cognitive"])
        
        with tabs[0]:  # Difficulty
            diff_stats = analyze_tag('Difficulty Level')
            for level in ['Easy', 'Medium', 'Hard']:
                if level in diff_stats:
                    st.write(f"**{level}**")
                    col1, col2 = st.columns(2)
                    col1.metric("Accuracy", f"{diff_stats[level]['accuracy']:.1f}%")
                    col2.metric("Avg Time", f"{diff_stats[level]['avg_time']:.1f}s")
        
        with tabs[1]:  # Question Type
            type_stats = analyze_tag('Question Type')
            if type_stats:
                st.bar_chart(pd.DataFrame(type_stats).T['accuracy'])
        
        with tabs[2]:  # Cognitive Level
            cog_stats = analyze_tag('Cognitive Level')
            for level in ['Remember', 'Understand', 'Apply', 'Analyze']:
                if level in cog_stats:
                    st.write(f"**{level}**")
                    st.progress(cog_stats[level]['accuracy']/100)

    # Recommendations
    st.header("🚀 Improvement Plan")
    
    # Weak subtopics
    subtopic_stats = analyze_tag('Sub- Topic')
    weak_subtopics = [k for k,v in subtopic_stats.items() if v['accuracy'] < 70]
    if weak_subtopics:
        st.error(f"**Focus Subtopics:** {', '.join(weak_subtopics)}")
    
    # Difficulty recommendations
    diff_stats = analyze_tag('Difficulty Level')
    weak_diff = [k for k,v in diff_stats.items() if v['accuracy'] < 70]
    if weak_diff:
        st.warning(f"**Practice More:** {', '.join(weak_diff)} level questions")
    
    # Cognitive recommendations
    cog_stats = analyze_tag('Cognitive Level')
    weak_cog = [k for k,v in cog_stats.items() if v['accuracy'] < 70]
    if weak_cog:
        st.info(f"**Develop Skills:** {', '.join(weak_cog)} level questions")

# Question display with error handling
def display_question(q):
    try:
        st.subheader(f"Question {st.session_state.current_question + 1}/{len(st.session_state.questions)}")
        st.markdown(f"**{q['Question Text']}**")
        
        options = [
            str(q['Option A']).strip(),
            str(q['Option B']).strip(),
            str(q['Option C']).strip(),
            str(q['Option D']).strip()
        ]
        
        answer = st.radio("Choose answer:", options, key=f"q{st.session_state.current_question}")
        
        if st.button("Next ➡️"):
            try:
                selected_index = options.index(answer.strip())
                selected_option = chr(65 + selected_index)
            except ValueError:
                st.error("Invalid selection! Please choose a valid option.")
                return
            
            st.session_state.user_answers[q['Question ID']] = {
                'selected': selected_option,
                'correct': q['Correct Answer'].strip().upper(),
                'time_taken': time.time() - st.session_state.start_time
            }
            
            st.session_state.current_question += 1
            st.session_state.start_time = time.time()
            st.rerun()
            
    except KeyError as e:
        st.error(f"Invalid question format: {str(e)}")
        st.session_state.current_question += 1
        st.rerun()

# Main app flow
def main():
    st.title("AI-Powered Mock Test Platform 🚀")
    
    if not st.session_state.authenticated:
        authenticate()
    else:
        if not st.session_state.questions:
            st.error("No valid questions found. Check data source!")
        elif not st.session_state.test_started:
            st.header(f"Welcome {st.session_state.username}!")
            st.write(f"Valid Questions: {len(st.session_state.questions)}")
            if st.button("Start Test 🚀"):
                st.session_state.test_started = True
                st.session_state.start_time = time.time()
                st.rerun()
        else:
            if st.session_state.current_question < len(st.session_state.questions):
                q = st.session_state.questions[st.session_state.current_question]
                display_question(q)
            else:
                show_results()
                if st.button("Retake Test 🔄"):
                    st.session_state.clear()
                    init_session()
                    st.rerun()

if __name__ == "__main__":
    main()
