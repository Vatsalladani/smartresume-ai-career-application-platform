"""SmartBuild Interview Service
Interactive guided resume builder with 3 modes:
1. BUILD_WITH_ME (Zero-to-One guided interview)
2. IMPROVE_RESUME (Strengthen weak bullets with concrete evidence)
3. CREATE_FOR_JOB (Targeted gap-filling for a specific JD)
Multilingual support: English, Hindi, Hinglish, Gujarati.
Anti-fabrication: Formulates STAR bullets only using user-provided facts.
"""
from typing import Any, Optional


QUESTIONS_BY_MODE_AND_LANG: dict[str, dict[str, list[dict[str, Any]]]] = {
    "BUILD_WITH_ME": {
        "en": [
            {
                "step": 1,
                "total_steps": 5,
                "category": "role_target",
                "question_text": "What is the primary role or job title you are targeting next?",
                "hint": "e.g. Senior Backend Engineer, Full-Stack Developer, Product Manager",
                "examples": ["Backend Python Engineer", "Frontend React Developer", "Data Scientist"],
                "field_key": "target_role"
            },
            {
                "step": 2,
                "total_steps": 5,
                "category": "primary_experience",
                "question_text": "Tell us about your most impactful recent project or job experience. What problem were you solving?",
                "hint": "Focus on the real business challenge and your specific contribution.",
                "examples": ["Built an async notification system for 100k users", "Migrated monolith to microservices"],
                "field_key": "experience_story"
            },
            {
                "step": 3,
                "total_steps": 5,
                "category": "metrics_and_scope",
                "question_text": "What real metrics or outcomes resulted from this work? (Never guess: if you don't know the exact percentage, describe the qualitative scale or volume).",
                "hint": "e.g., Reduced latency from 400ms to 90ms; Handled 5,000 requests/sec; Saved 10 developer hours/week.",
                "examples": ["Cut server costs by 22%", "Zero downtime migration over 3 months"],
                "field_key": "real_metrics"
            },
            {
                "step": 4,
                "total_steps": 5,
                "category": "tools_and_technologies",
                "question_text": "Which technologies, libraries, databases, and tools did you personally use hands-on?",
                "hint": "List only tools you can confidently explain in an interview.",
                "examples": ["FastAPI, PostgreSQL, Redis, Docker, AWS ECS", "React, TypeScript, Tailwind CSS"],
                "field_key": "hands_on_tools"
            },
            {
                "step": 5,
                "total_steps": 5,
                "category": "education_credentials",
                "question_text": "What degree, college/university, graduation year, and certifications do you hold?",
                "hint": "Include official degree name and institution.",
                "examples": ["B.Tech in Computer Science, 2023, Tier 1 University", "AWS Certified Solutions Architect"],
                "field_key": "education_history"
            }
        ],
        "hi": [
            {
                "step": 1,
                "total_steps": 5,
                "category": "role_target",
                "question_text": "आप किस रोल या जॉब के लिए आवेदन करना चाहते हैं?",
                "hint": "उदाहरण: Senior Python Engineer, Data Analyst, Product Manager",
                "examples": ["Backend Developer", "Full Stack Engineer"],
                "field_key": "target_role"
            },
            {
                "step": 2,
                "total_steps": 5,
                "category": "primary_experience",
                "question_text": "अपने सबसे मुख्य प्रोजेक्ट या हालिया काम के बारे में बताएं। आपने क्या समस्या हल की?",
                "hint": "कंपनी या क्लाइंट की असली समस्या और अपने योगदान पर ध्यान दें।",
                "examples": ["1 लाख यूज़र्स के लिए एपीआई बनाई", "डेटाबेस की स्पीड बेहतर की"],
                "field_key": "experience_story"
            },
            {
                "step": 3,
                "total_steps": 5,
                "category": "metrics_and_scope",
                "question_text": "इस काम के क्या परिणाम मिले? कोई वास्तविक आंकड़े (metrics) बताइए (अंदाज़ा न लगाएं)।",
                "hint": "जैसे: लेटेंसी 30% घटी, 5000 ऑर्डर्स प्रोसेस किए।",
                "examples": ["लोड टाइम 2 सेकंड कम हुआ"],
                "field_key": "real_metrics"
            },
            {
                "step": 4,
                "total_steps": 5,
                "category": "tools_and_technologies",
                "question_text": "आपने वास्तव में किन टूल्स, लैंग्वेजेस और डेटाबेस का उपयोग किया?",
                "hint": "सिर्फ वही लिखें जिनका इंटरव्यू में जवाब दे सकें।",
                "examples": ["Python, Django, PostgreSQL, Docker"],
                "field_key": "hands_on_tools"
            },
            {
                "step": 5,
                "total_steps": 5,
                "category": "education_credentials",
                "question_text": "आपकी डिग्री, कॉलेज का नाम और पासिंग ईयर क्या है?",
                "hint": "B.Tech, BCA, MCA, आदि।",
                "examples": ["B.Tech Computer Science, 2022"],
                "field_key": "education_history"
            }
        ],
        "hinglish": [
            {
                "step": 1,
                "total_steps": 5,
                "category": "role_target",
                "question_text": "Aap kis role ya job title ke liye apply karna chahte hain?",
                "hint": "e.g. Senior Backend Engineer, React Developer, DevOps Specialist",
                "examples": ["Backend Engineer", "Data Analyst"],
                "field_key": "target_role"
            },
            {
                "step": 2,
                "total_steps": 5,
                "category": "primary_experience",
                "question_text": "Apne sabse impactful project ya experience ke baare me bataiye. Aapne kya problem solve ki?",
                "hint": "Asli challenges aur apne contribution par focus karein.",
                "examples": ["Payment gateway integrate kiya", "Legacy code modernize kiya"],
                "field_key": "experience_story"
            },
            {
                "step": 3,
                "total_steps": 5,
                "category": "metrics_and_scope",
                "question_text": "Is kaam se business ko kya real benefit ya metric mila? (Guess mat kijiye, real facts likhiye)",
                "hint": "e.g., API response time 50% improve hua, 10k users handle kiye.",
                "examples": ["Response time 200ms se 50ms ho gaya"],
                "field_key": "real_metrics"
            },
            {
                "step": 4,
                "total_steps": 5,
                "category": "tools_and_technologies",
                "question_text": "Kaun se frameworks, languages, aur databases aapne personally use kiye?",
                "hint": "Wohi tools likhiye jinka deep knowledge ho.",
                "examples": ["FastAPI, PostgreSQL, Redis, Docker"],
                "field_key": "hands_on_tools"
            },
            {
                "step": 5,
                "total_steps": 5,
                "category": "education_credentials",
                "question_text": "Aapki degree, college name, aur graduation year kya hai?",
                "hint": "Degree, institution name, year.",
                "examples": ["B.E. Information Technology, 2021"],
                "field_key": "education_history"
            }
        ],
        "gu": [
            {
                "step": 1,
                "total_steps": 5,
                "category": "role_target",
                "question_text": "તમે કયા રોલ અથવા પદ માટે અરજી કરવા માંગો છો?",
                "hint": "દા.ત. સોફ્ટવેર એન્જિનિયર, ડેટા વિશ્લેષક",
                "examples": ["Python Developer", "Full Stack Engineer"],
                "field_key": "target_role"
            },
            {
                "step": 2,
                "total_steps": 5,
                "category": "primary_experience",
                "question_text": "તમારા સૌથી મહત્વપૂર્ણ પ્રોજેક્ટ વિશે જણાવો. તમે કઈ મુશ્કેલી હલ કરી હતી?",
                "hint": "તમારું વ્યક્તિગત યોગદાન જણાવો.",
                "examples": ["વેબસાઇટની ગતિ સુધારી", "નવું પેમેન્ટ મોડ્યુલ બનાવ્યું"],
                "field_key": "experience_story"
            },
            {
                "step": 3,
                "total_steps": 5,
                "category": "metrics_and_scope",
                "question_text": "આ કામથી શું વાસ્તવિક ફાયદો થયો? કોઈ માપી શકાય તેવા પરિણામો?",
                "hint": "અંદાજ લગાવશો નહીં, સાચી માહિતી આપો.",
                "examples": ["લોડ ટાઈમ ૪૦% ઘટ્યો"],
                "field_key": "real_metrics"
            },
            {
                "step": 4,
                "total_steps": 5,
                "category": "tools_and_technologies",
                "question_text": "તમે કઈ તકનીકો અને સોફ્ટવેરનો ઉપયોગ કર્યો હતો?",
                "hint": "ફક્ત તમે જે જાણો છો તે જ લખો.",
                "examples": ["Python, PostgreSQL, Git"],
                "field_key": "hands_on_tools"
            },
            {
                "step": 5,
                "total_steps": 5,
                "category": "education_credentials",
                "question_text": "તમારી ડિગ્રી અને કોલેજનું નામ જણાવો.",
                "hint": "B.Tech, BCA, વગેરે.",
                "examples": ["B.Tech Computer Science, 2022"],
                "field_key": "education_history"
            }
        ]
    },
    "IMPROVE_RESUME": {
        "en": [
            {
                "step": 1,
                "total_steps": 3,
                "category": "bullet_strengthening",
                "question_text": "Paste one of your current resume bullet points that feels weak or generic.",
                "hint": "e.g. 'Responsible for developing web applications'",
                "examples": ["Worked on frontend bugs", "Assisted in database maintenance"],
                "field_key": "weak_bullet"
            },
            {
                "step": 2,
                "total_steps": 3,
                "category": "real_scope",
                "question_text": "What was the real outcome of this work? What broke if you didn't do it, or what improved?",
                "hint": "Be specific about the user or team benefit.",
                "examples": ["Fixed 35 checkout bugs preventing cart dropoffs", "Automated backup script saving 3 hours"],
                "field_key": "bullet_outcome"
            },
            {
                "step": 3,
                "total_steps": 3,
                "category": "tools_used",
                "question_text": "What specific tools or libraries enabled you to achieve this?",
                "hint": "Frameworks, databases, protocols.",
                "examples": ["React Profiler, Chrome DevTools", "pg_stat_statements, indexing"],
                "field_key": "bullet_tools"
            }
        ]
    },
    "CREATE_FOR_JOB": {
        "en": [
            {
                "step": 1,
                "total_steps": 3,
                "category": "jd_requirements",
                "question_text": "Paste the primary requirements or core responsibilities from the Job Description.",
                "hint": "Copy the key 4-6 requirement bullets from the JD.",
                "examples": ["5+ years with distributed systems, experience with Kafka, AWS, high throughput"],
                "field_key": "jd_text"
            },
            {
                "step": 2,
                "total_steps": 3,
                "category": "matching_evidence",
                "question_text": "Which of these requirements have you handled directly in the past? Give 1-2 factual sentences for each.",
                "hint": "Do not claim experience you do not have. We will highlight your real strengths honestly.",
                "examples": ["I built event-driven pipelines using Kafka at Acme Corp with 2M messages/day."],
                "field_key": "candidate_matching_facts"
            },
            {
                "step": 3,
                "total_steps": 3,
                "category": "gap_handling",
                "question_text": "Are there any required tools in the JD you haven't used yet? Mention related tools you DO know.",
                "hint": "e.g., 'Haven't used GCP, but 3 years in AWS' or 'Haven't used Vue, but expert in React'.",
                "examples": ["No Kubernetes experience, but strong Docker containerization experience."],
                "field_key": "candidate_adjacent_skills"
            }
        ]
    }
}


def get_questions_for_session(mode: str = "BUILD_WITH_ME", language: str = "en") -> list[dict[str, Any]]:
    mode_dict = QUESTIONS_BY_MODE_AND_LANG.get(mode, QUESTIONS_BY_MODE_AND_LANG["BUILD_WITH_ME"])
    lang_questions = mode_dict.get(language, mode_dict.get("en", []))
    return lang_questions


def synthesize_star_bullet(action: str, metric: str, tools: str) -> str:
    """Combines user answers into a strict STAR bullet without fabricating data."""
    action_clean = action.strip().rstrip(".")
    tools_clean = tools.strip()
    metric_clean = metric.strip().rstrip(".")

    bullet_parts = []
    if action_clean:
        bullet_parts.append(action_clean)
    if tools_clean and tools_clean.lower() not in action_clean.lower():
        bullet_parts.append(f"utilizing {tools_clean}")
    if metric_clean and metric_clean.lower() != "none" and metric_clean.lower() != "na":
        bullet_parts.append(f"resulting in {metric_clean}")

    bullet = ", ".join(bullet_parts)
    if bullet and not bullet.endswith("."):
        bullet += "."
    return bullet
