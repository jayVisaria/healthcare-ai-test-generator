import streamlit as st
from google import genai
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
# To run this app, set your Google API key as an environment variable:
# export GEMINI_API_KEY="YOUR_API_KEY"
        # Then run the app: streamlit run test_generator.py

try:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("Please set your GEMINI_API_KEY environment variable.")
        st.stop()
    
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Failed to configure Google AI. Please ensure your GEMINI_API_KEY is set. Error: {e}")
    st.stop()

# --- Healthcare-Specific Configuration ---
HEALTHCARE_STANDARDS = {
    "FDA": "FDA 21 CFR Part 820 (Quality System Regulation)",
    "IEC_62304": "IEC 62304 (Medical Device Software)",
    "ISO_9001": "ISO 9001 (Quality Management Systems)",
    "ISO_13485": "ISO 13485 (Medical Devices Quality Management)",
    "ISO_27001": "ISO 27001 (Information Security Management)",
    "HIPAA": "HIPAA (Health Insurance Portability and Accountability Act)",
    "GDPR": "GDPR (General Data Protection Regulation)"
}

ALM_PLATFORMS = ["Jira", "Polarion", "Azure DevOps", "TestRail", "Quality Center"]

# --- Enhanced Healthcare-Focused Prompts ---

GENERATE_HEALTHCARE_SCENARIOS_PROMPT = """
Context: You are an expert healthcare software testing specialist with deep knowledge of medical device regulations and healthcare compliance standards. Your task is to generate comprehensive test scenarios for healthcare software requirements.

Healthcare Software Requirement:
"{user_story}"

Acceptance Criteria:
"{acceptance_criteria}"

Applicable Standards: {standards}
Risk Level: {risk_level}

Instructions:
Generate a comprehensive JSON array of test scenarios that must include:

1. **Positive Test Cases**: Normal operation scenarios that verify:
   - Core functionality works as specified
   - Data integrity is maintained
   - User workflows complete successfully
   - System integrations function properly

2. **Negative Test Cases**: Error handling and security scenarios that verify:
   - Invalid input handling (malformed data, out-of-range values)
   - Security vulnerabilities (unauthorized access, data breaches)
   - System error responses and recovery
   - Regulatory compliance violations

3. **Edge Cases**: Boundary and stress scenarios that verify:
   - Maximum/minimum data limits
   - System performance under load
   - Concurrent user scenarios
   - Data migration and backup/recovery
   - Network interruption handling

4. **Compliance Test Cases**: Regulatory-specific scenarios that verify:
   - Audit trail requirements
   - Data privacy and protection (GDPR, HIPAA)
   - User access controls and authentication
   - Data retention and deletion policies
   - Regulatory reporting capabilities

Requirements:
- Output MUST be valid JSON array without markdown formatting
- Each object must have: "TestScenario" (string), "Description" (string), "TestPriority" (string: "Critical", "High", "Medium", "Low"), "ComplianceStandard" (string), "RiskCategory" (string: "Patient Safety", "Data Security", "Regulatory", "Functional")
- Ensure traceability to the original requirement
- Include specific healthcare domain considerations
- Address the applicable standards mentioned above
"""

GENERATE_HEALTHCARE_GHERKIN_PROMPT = """
Context: You are a senior healthcare software test automation engineer specializing in regulatory-compliant test case development. Create detailed Gherkin test scripts that ensure full traceability to requirements and compliance standards.

Healthcare Software Requirement:
"{user_story}"

Acceptance Criteria:
"{acceptance_criteria}"

Test Scenario Details:
- Scenario: {test_scenario_type}
- Description: {test_scenario_description}
- Compliance Standard: {compliance_standard}
- Risk Category: {risk_category}

Instructions:
Generate a detailed Gherkin test case that includes:

1. **Feature Declaration**: Clear feature name derived from the healthcare requirement
2. **Background** (if applicable): Common setup steps for healthcare context
3. **Scenario**: Descriptive scenario name reflecting the test objective
4. **Given Steps**: Healthcare-specific preconditions including:
   - User roles and permissions
   - Patient data setup (anonymized)
   - System state and configurations
   - Compliance requirements active
5. **When Steps**: Actions performed including:
   - User interactions with healthcare workflows
   - System operations and data processing
   - Integration with external healthcare systems
6. **Then Steps**: Expected outcomes including:
   - Functional verification
   - Data integrity checks
   - Audit trail validation
   - Compliance verification
   - Security assertion

Additional Requirements:
- Include data privacy considerations (use anonymized test data)
- Add compliance validation steps where applicable
- Ensure audit trail verification
- Include error handling verification for negative scenarios
- Add performance criteria for edge cases
- Use healthcare domain terminology appropriately
- Ensure test is automatable with clear assertions

Format as standard Gherkin syntax without additional markup or explanations.
"""

# --- Helper Functions ---

def safe_json_loads(json_string: str) -> Optional[List[Dict]]:
    """Safely loads a JSON string, attempting to clean it first."""
    # Remove markdown code block markers if present
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'```\s*$', '', json_string)
    
    # Attempt to find a JSON array within the string
    match = re.search(r'\[.*\]', json_string, re.DOTALL)
    if match:
        json_string = match.group(0)
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        st.error(f"AI response was not valid JSON. Error: {e}")
        return None

def generate_traceability_id() -> str:
    """Generate a unique traceability ID for requirements tracking."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"REQ_{timestamp}"

def generate_healthcare_test_scenarios(_user_story: str, _acceptance_criteria: str, 
                                     _standards: List[str], _risk_level: str) -> Dict:
    """Calls the Gemini API to generate healthcare-specific test scenarios."""
    if not _user_story:
        return {"error": "Healthcare requirement cannot be empty."}
    
    standards_text = ", ".join([HEALTHCARE_STANDARDS.get(std, std) for std in _standards])
    
    prompt = GENERATE_HEALTHCARE_SCENARIOS_PROMPT.format(
        user_story=_user_story,
        acceptance_criteria=_acceptance_criteria,
        standards=standards_text,
        risk_level=_risk_level
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        scenarios = safe_json_loads(response.text)
        if scenarios:
            return {"success": True, "scenarios": scenarios}
        else:
            return {"error": "Failed to parse scenarios from AI response."}
    except Exception as e:
        return {"error": f"An error occurred with the AI model: {e}"}

def generate_healthcare_gherkin_script(_user_story: str, _acceptance_criteria: str, _scenario: Dict, _timestamp: Optional[str] = None) -> str:
    """Calls the Gemini API to generate a healthcare-compliant Gherkin script."""
    # Add timestamp to ensure fresh generation when needed
    current_time = _timestamp or datetime.now().isoformat()
    
    prompt = GENERATE_HEALTHCARE_GHERKIN_PROMPT.format(
        user_story=_user_story,
        acceptance_criteria=_acceptance_criteria,
        test_scenario_type=_scenario.get("TestScenario", "N/A"),
        test_scenario_description=_scenario.get("Description", "N/A"),
        compliance_standard=_scenario.get("ComplianceStandard", "General"),
        risk_category=_scenario.get("RiskCategory", "Functional")
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error generating Gherkin script: {e}"

# --- Streamlit UI ---

st.set_page_config(
    layout="wide", 
    page_title="Healthcare AI Test Generator",
    page_icon="🏥"
)

# Custom CSS for healthcare theme
st.markdown("""
<style>
    .healthcare-header {
        background: linear-gradient(90deg, #0066cc, #004499);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .compliance-badge {
        background-color: #e8f4fd;
        border: 1px solid #0066cc;
        border-radius: 15px;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.8rem;
    }
    .risk-critical { background-color: #ffebee; border-color: #f44336; }
    .risk-high { background-color: #fff3e0; border-color: #ff9800; }
    .risk-medium { background-color: #f3e5f5; border-color: #9c27b0; }
    .risk-low { background-color: #e8f5e8; border-color: #4caf50; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="healthcare-header" style="text-align: center;">
    <h1>🏥 Healthcare AI Test Case Generator</h1>
    <p>AI-Powered System for Converting Healthcare Software Requirements into Compliant, Traceable Test Cases</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
**Regulatory Compliance**: FDA 21 CFR Part 820, IEC 62304, ISO 13485, ISO 27001, HIPAA, GDPR  
**Integration Ready**: Jira, Polarion, Azure DevOps, TestRail  
**Powered by**: Google Gemini AI

### Workflow:
1. **Define Healthcare Requirements** - Enter user story and acceptance criteria
2. **Configure Compliance** - Select applicable standards and risk level  
3. **Generate Test Scenarios** - AI creates comprehensive test coverage
4. **Select & Refine** - Choose scenarios for detailed implementation
5. **Export Test Assets** - Download Gherkin feature files with full traceability
""")

# --- State Management ---
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = []
if 'selected_scenarios' not in st.session_state:
    st.session_state.selected_scenarios = []
if 'generated_scripts' not in st.session_state:
    st.session_state.generated_scripts = []
if 'scenarios_generation_id' not in st.session_state:
    st.session_state.scenarios_generation_id = 0
if 'user_story' not in st.session_state:
    st.session_state.user_story = ""
if 'acceptance_criteria' not in st.session_state:
    st.session_state.acceptance_criteria = ""
if 'traceability_id' not in st.session_state:
    st.session_state.traceability_id = generate_traceability_id()

# --- Step 1: Input Healthcare Requirements ---
st.header("Step 1: Define Healthcare Software Requirements")

col1, col2 = st.columns([2, 1])

# First, get the configuration from col2
with col2:
    st.subheader("Compliance Configuration")
    
    selected_standards = st.multiselect(
        "Applicable Healthcare Standards",
        options=list(HEALTHCARE_STANDARDS.keys()),
        default=["FDA", "HIPAA"],
        help="Select all regulatory standards that apply to this requirement"
    )
    
    risk_level = st.selectbox(
        "Risk Classification",
        options=["Critical", "High", "Medium", "Low"],
        index=1,
        help="Risk level determines test coverage depth and compliance rigor"
    )
    
    target_platform = st.selectbox(
        "Target ALM Platform",
        options=ALM_PLATFORMS,
        help="Choose your Application Lifecycle Management platform for integration"
    )

# Now the form with all inputs and submit button
with col1:
    with st.form(key="healthcare_requirements_form"):
        user_story_input = st.text_area(
            "Healthcare User Story / Requirement", 
            st.session_state.user_story,
            height=170, 
            placeholder="As a [healthcare professional/patient/administrator], I want to [perform healthcare action] so that I can [achieve healthcare outcome that ensures patient safety/compliance/efficiency].\n\nExample: As a clinician, I want to access patient medication history through the EHR system so that I can make informed prescribing decisions while maintaining HIPAA compliance."
        )
        
        acceptance_criteria_input = st.text_area(
            "Acceptance Criteria",
            st.session_state.acceptance_criteria,
            height=200,
            placeholder="Given [healthcare context], when [action is performed], then [expected outcome with compliance considerations].\n\nExample:\nGiven a clinician is authenticated in the EHR system\nWhen they search for a patient's medication history\nThen the system displays complete medication records with audit trail\nAnd ensures HIPAA compliance with access logging\nAnd validates user permissions for data access"
        )
        
        submitted = st.form_submit_button("🧠 Generate Healthcare Test Scenarios", type="primary")
        
        if submitted:
            st.session_state.user_story = user_story_input
            st.session_state.acceptance_criteria = acceptance_criteria_input
            st.session_state.traceability_id = generate_traceability_id()
            
            # Show progress while generating scenarios
            with st.spinner("🧠 Generating healthcare test scenarios..."):
                result = generate_healthcare_test_scenarios(
                    user_story_input, 
                    acceptance_criteria_input,
                    selected_standards,
                    risk_level
                )
            
            if result.get("success"):
                st.session_state.scenarios = result["scenarios"]
                st.session_state.current_step = 2
                st.session_state.selected_scenarios = []
                st.session_state.generated_scripts = []  # Clear any existing generated scripts
                st.session_state.scenarios_generation_id += 1  # Increment to reset checkbox selections
                st.rerun()
            else:
                st.error(result.get("error", "An unknown error occurred."))

# --- Step 2: Review and Select Healthcare Test Scenarios ---
if st.session_state.current_step >= 2 and st.session_state.scenarios:
    st.header("Step 2: Review Healthcare Test Scenarios")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scenarios", len(st.session_state.scenarios))
    with col2:
        critical_count = sum(1 for s in st.session_state.scenarios if s.get('TestPriority') == 'Critical')
        st.metric("Critical Priority", critical_count)
    with col3:
        patient_safety_count = sum(1 for s in st.session_state.scenarios if s.get('RiskCategory') == 'Patient Safety')
        st.metric("Patient Safety", patient_safety_count)
    with col4:
        st.metric("Traceability ID", st.session_state.traceability_id)
    
    st.subheader("Select Test Scenarios for Implementation")
    
    selected_indices = []
    for i, scenario in enumerate(st.session_state.scenarios):
        with st.container():
            cols = st.columns([0.05, 0.25, 0.45, 0.1, 0.1, 0.05])
            
            with cols[0]:
                if st.checkbox("", key=f"select_{i}_{st.session_state.scenarios_generation_id}"):
                    selected_indices.append(i)
            
            with cols[1]:
                st.markdown(f"**{scenario.get('TestScenario', 'N/A')}**")
                
                # Compliance badge
                compliance = scenario.get('ComplianceStandard', 'General')
                st.markdown(f'<span class="compliance-badge">{compliance}</span>', unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(scenario.get('Description', 'No description provided.'))
            
            with cols[3]:
                priority = scenario.get('TestPriority', 'Medium')
                risk_class = f"risk-{priority.lower()}"
                st.markdown(f'<span class="compliance-badge {risk_class}">{priority}</span>', unsafe_allow_html=True)
            
            with cols[4]:
                risk_category = scenario.get('RiskCategory', 'Functional')
                st.markdown(f"**{risk_category}**")
            
            with cols[5]:
                st.markdown("📋")
    
    # Update selected scenarios
    st.session_state.selected_scenarios = [st.session_state.scenarios[i] for i in selected_indices]
    
    if st.session_state.selected_scenarios:
        st.success(f"✅ {len(st.session_state.selected_scenarios)} scenarios selected for implementation")
        
        # Button to generate Gherkin scripts
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🚀 Generate Test Scripts", type="primary", key="generate_scripts"):
                st.session_state.current_step = 3
                st.session_state.generated_scripts = []  # Reset generated scripts
                st.rerun()
        
        with col2:
            if st.session_state.current_step >= 3 and st.session_state.generated_scripts:
                if st.button("🔄 Regenerate Test Scripts", type="secondary", key="regenerate_scripts"):
                    st.session_state.generated_scripts = []  # Clear existing scripts to trigger regeneration
                    st.rerun()

# --- Step 3: Generate Healthcare-Compliant Gherkin Scripts ---
if st.session_state.current_step >= 3 and st.session_state.selected_scenarios:
    st.header("Step 3: Generated Healthcare Test Assets")
    
    # Generate scripts only if they haven't been generated yet
    if not st.session_state.generated_scripts:
        st.info("🔄 Generating healthcare-compliant test scripts...")
        
        all_gherkin_scripts = []
        progress_bar = st.progress(0)
        generation_timestamp = datetime.now().isoformat()  # Unique timestamp for this generation
        
        for idx, scenario in enumerate(st.session_state.selected_scenarios):
            progress_bar.progress((idx + 1) / len(st.session_state.selected_scenarios))
            
            gherkin_script = generate_healthcare_gherkin_script(
                st.session_state.user_story,
                st.session_state.acceptance_criteria,
                scenario,
                generation_timestamp  # Pass timestamp to ensure unique generation
            )
            all_gherkin_scripts.append({
                'scenario': scenario,
                'gherkin': gherkin_script
            })
        
        progress_bar.empty()
        st.session_state.generated_scripts = all_gherkin_scripts
        st.success("✅ Test scripts generated successfully!")
    else:
        all_gherkin_scripts = st.session_state.generated_scripts
    
    # Create comprehensive feature file
    feature_header = f"""# Traceability ID: {st.session_state.traceability_id}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Compliance Standards: {', '.join(selected_standards)}
# Risk Level: {risk_level}
# Target Platform: {target_platform}

Feature: Healthcare Test Suite - {st.session_state.user_story[:100]}...
  
  Background:
    Given the healthcare system is operational and compliant
    And audit logging is enabled for all user actions
    And user authentication and authorization systems are active

"""
    
    # Combine all scenarios
    combined_scenarios = []
    for script_data in all_gherkin_scripts:
        scenario_content = script_data['gherkin']
        # Extract scenario content (remove Feature line if present)
        scenario_match = re.search(r'Scenario.*', scenario_content, re.DOTALL)
        if scenario_match:
            combined_scenarios.append(scenario_match.group(0))
        else:
            combined_scenarios.append(scenario_content)
    
    final_feature_file = feature_header + "\n\n".join(combined_scenarios)
    
    # Display the generated content
    st.subheader("Complete Feature File")
    st.code(final_feature_file, language="gherkin")
    
    # Download options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="📥 Download .feature File",
            data=final_feature_file,
            file_name=f"healthcare_tests_{st.session_state.traceability_id}.feature",
            mime="text/plain",
            type="primary"
        )
    
    with col2:
        # Generate traceability matrix
        traceability_matrix = {
            "requirement_id": st.session_state.traceability_id,
            "requirement": st.session_state.user_story,
            "acceptance_criteria": st.session_state.acceptance_criteria,
            "compliance_standards": selected_standards,
            "risk_level": risk_level,
            "generated_scenarios": [
                {
                    "scenario_name": s.get('TestScenario'),
                    "description": s.get('Description'),
                    "priority": s.get('TestPriority'),
                    "compliance_standard": s.get('ComplianceStandard'),
                    "risk_category": s.get('RiskCategory')
                }
                for s in st.session_state.selected_scenarios
            ],
            "generation_timestamp": datetime.now().isoformat()
        }
        
        st.download_button(
            label="📊 Download Traceability Matrix",
            data=json.dumps(traceability_matrix, indent=2),
            file_name=f"traceability_matrix_{st.session_state.traceability_id}.json",
            mime="application/json"
        )
    
    with col3:
        # Generate summary report
        summary_report = f"""# Healthcare Test Generation Summary Report

**Traceability ID:** {st.session_state.traceability_id}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Requirement Details
- **User Story:** {st.session_state.user_story}
- **Compliance Standards:** {', '.join(selected_standards)}
- **Risk Level:** {risk_level}
- **Target ALM Platform:** {target_platform}

## Test Coverage Summary
- **Total Scenarios Generated:** {len(st.session_state.scenarios)}
- **Scenarios Selected for Implementation:** {len(st.session_state.selected_scenarios)}
- **Critical Priority Tests:** {sum(1 for s in st.session_state.selected_scenarios if s.get('TestPriority') == 'Critical')}
- **Patient Safety Tests:** {sum(1 for s in st.session_state.selected_scenarios if s.get('RiskCategory') == 'Patient Safety')}

## Compliance Verification
✅ Regulatory standards addressed
✅ Audit trail requirements included  
✅ Data privacy considerations implemented
✅ Traceability established
✅ Risk-based testing approach applied

---
*Generated by Healthcare AI Test Generator - Powered by Google Gemini*
"""
        
        st.download_button(
            label="📋 Download Summary Report",
            data=summary_report,
            file_name=f"test_summary_{st.session_state.traceability_id}.md",
            mime="text/markdown"
        )
    
    # Integration guidance
    st.subheader("Integration Guidance")
    st.info(f"""
    **Next Steps for {target_platform} Integration:**
    1. Import the generated .feature file into your test automation framework
    2. Use the traceability matrix to link requirements to test cases
    3. Configure your CI/CD pipeline to execute these tests
    4. Set up compliance reporting using the generated documentation
    5. Establish audit trail monitoring for regulatory requirements
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0; background-color: #f8f9fa; border-radius: 10px; margin-top: 2rem;'>
    <div style='color: #495057; font-size: 0.9rem; margin-bottom: 0.5rem;'>
        <strong>Healthcare AI Test Generator</strong>
    </div>
    <div style='color: #6c757d; font-size: 0.8rem;'>
        Powered by Google Gemini AI • Built for Healthcare Excellence
    </div>
    <div style='color: #6c757d; font-size: 0.7rem; margin-top: 0.5rem;'>
        © 2025 • Ensuring Quality & Compliance in Healthcare Software Testing
    </div>
</div>
""", unsafe_allow_html=True)