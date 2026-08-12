"""
Bilingual (EN/ES) content for app.py.

Two kinds of content live here:
  - UI: static interface strings, looked up with t(lang, key).
  - Translations of the *dynamic* content that comes out of
    Digital_readiness_tool_Framework.xlsx (which is English-only): dimension
    names/questions, level names/descriptions, next-step text and solution
    value props. Those are keyed by the exact English string from the
    workbook so translate_fw(lang, text) can look a value up regardless of
    which sheet/column it came from. If a string isn't found (e.g. the
    workbook was edited and a new level/solution added), the English text is
    shown as a safe fallback rather than crashing.
"""

from __future__ import annotations

DIMENSION_NAMES: dict[str, dict[str, str]] = {
    "en": {
        "strategy": "Strategy",
        "people": "People",
        "operations": "Operations",
        "connectivity": "Connectivity",
        "intelligence": "Intelligence",
    },
    "es": {
        "strategy": "Estrategia",
        "people": "Personas",
        "operations": "Operaciones",
        "connectivity": "Conectividad",
        "intelligence": "Inteligencia",
    },
}

DIMENSION_ICONS: dict[str, str] = {
    "strategy": "🎯",
    "people": "👥",
    "operations": "⚙️",
    "connectivity": "🔗",
    "intelligence": "🧠",
}

KPI_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "oee": "Potential OEE Improvement",
        "quality": "Potential Quality Cost Reduction",
        "energy": "Potential Energy Savings",
        "stock": "Potential Stock Turnover Improvement",
    },
    "es": {
        "oee": "Mejora Potencial de OEE",
        "quality": "Reducción Potencial de Costos de Calidad",
        "energy": "Ahorro Potencial de Energía",
        "stock": "Mejora Potencial en Rotación de Inventario",
    },
}

# ---------------------------------------------------------------------------
# English -> Spanish lookup for workbook-sourced text.
# ---------------------------------------------------------------------------
_ES_LOOKUP: dict[str, str] = {
    # Dimension questions
    "Are you investing in the right opportunities?": "¿Estás invirtiendo en las oportunidades correctas?",
    "Can your people drive and sustain change?": "¿Tu gente puede impulsar y sostener el cambio?",
    "Do you control and continuously improve operations?": "¿Controlas y mejoras continuamente tus operaciones?",
    "Can information flow across our factory and business?": "¿Puede la información fluir a través de tu planta y tu negocio?",
    "Can you turn information into business value?": "¿Puedes convertir la información en valor de negocio?",

    # Strategy levels
    "No automation and digital strategy": "Sin estrategia de automatización y digital",
    "No formal Automation & Digital strategy exists. Investments are made reactively to address immediate operational issues.":
        "No existe una estrategia formal de Automatización y Digital. Las inversiones se realizan de forma reactiva para resolver problemas operativos inmediatos.",
    "Visibility of current automation and digital maturity": "Visibilidad de la madurez actual de automatización y digital",
    "The current status of assets, automation systems and digital capabilities is understood, but improvement actions remain ad hoc.":
        "Se comprende el estado actual de los activos, sistemas de automatización y capacidades digitales, pero las acciones de mejora siguen siendo puntuales.",
    "Defined automation and digital strategy": "Estrategia de automatización y digital definida",
    "Clear vision of how digitalization supports business objectives.": "Visión clara de cómo la digitalización apoya los objetivos de negocio.",
    "Transformation roadmap and investment prioritization": "Hoja de ruta de transformación y priorización de inversión",
    "Projects are selected through ROI, business cases and strategic impact":
        "Los proyectos se seleccionan según el ROI, casos de negocio e impacto estratégico.",
    "Digital governance": "Gobernanza digital",
    "Digital board with KPI tracking, value realization, benefits measurement and continuous portfolio review.":
        "Tablero digital con seguimiento de KPI, realización de valor, medición de beneficios y revisión continua del portafolio.",
    "Quantify business impact and continuously optimize your transformation portfolio.":
        "Cuantifica el impacto de negocio y optimiza continuamente tu portafolio de transformación.",

    # People levels
    "Training": "Capacitación",
    "Structured programs exist to build required capabilities.": "Existen programas estructurados para desarrollar las capacidades requeridas.",
    "Capability assessment": "Evaluación de capacidades",
    "Skills and readiness are evaluated": "Se evalúan las habilidades y la preparación del equipo.",
    "Cross-functional collaboration": "Colaboración multifuncional",
    "Teams collaborate effectively across functions using digital tools and common processes.":
        "Los equipos colaboran eficazmente entre funciones usando herramientas digitales y procesos comunes.",
    "Leadership sponsorship": "Patrocinio del liderazgo",
    "Leaders actively promote and support transformation.": "Los líderes promueven y respaldan activamente la transformación.",
    "Change management culture": "Cultura de gestión del cambio",
    "Change and digital adoption are embedded in the culture and continuously reinforced across the organization.":
        "El cambio y la adopción digital están integrados en la cultura y se refuerzan continuamente en toda la organización.",
    "Scale successful initiatives across the organization": "Escala las iniciativas exitosas a toda la organización.",

    # Operations levels
    "Corrective actions (firefighting)": "Acciones correctivas (apagar incendios)",
    "Problems are addressed only after they occur.": "Los problemas se atienden solo después de que ocurren.",
    "Standardized and documented procedures": "Procedimientos estandarizados y documentados",
    "Processes are consistent and repeatable.": "Los procesos son consistentes y repetibles.",
    "Performance management": "Gestión del desempeño",
    "Operational KPIs are measured, tracked and reviewed regularly.": "Los KPI operativos se miden, monitorean y revisan periódicamente.",
    "Preventive improvement (root-cause analysis)": "Mejora preventiva (análisis de causa raíz)",
    "Root cause analysis drives preventive actions and systematic improvement.":
        "El análisis de causa raíz impulsa acciones preventivas y mejora sistemática.",
    "Continuous improvement culture": "Cultura de mejora continua",
    "Continuous improvement is embedded in daily operations and supported by data-driven decision making.":
        "La mejora continua está integrada en las operaciones diarias y respaldada por decisiones basadas en datos.",
    "Replicate best practices across the organization and benchmark performance externally.":
        "Replica las mejores prácticas en toda la organización y compara el desempeño externamente.",

    # Connectivity levels
    "Know your installed base": "Conoce tu base instalada",
    "Inventory and assessment of automation assets (PLC, HMI, drives, SCADA)\nIdentification of risks and unsupported systems\nModernization strategy defined":
        "Inventario y evaluación de activos de automatización (PLC, HMI, variadores, SCADA)\nIdentificación de riesgos y sistemas sin soporte\nEstrategia de modernización definida",
    "Up-to-date automation and production control": "Automatización y control de producción actualizados",
    "One control room: equipment can communicate and are visible within the factory":
        "Una sala de control: los equipos pueden comunicarse y son visibles dentro de la planta.",
    "Connected assets and data collection": "Activos conectados y recolección de datos",
    "Operational data is automatically gathered from equipment and processes.":
        "Los datos operativos se recopilan automáticamente de los equipos y procesos.",
    "OT/IT integration (Digital Bridge)": "Integración OT/IT (Digital Bridge)",
    "Shopfloor systems are connected with MES, ERP and business applications.":
        "Los sistemas de planta están conectados con MES, ERP y aplicaciones de negocio.",
    "Secure Connected Factory": "Fábrica Conectada Segura",
    "Factory systems and business applications are securely connected, with cybersecurity measures protecting operations, data and remote access.":
        "Los sistemas de planta y las aplicaciones de negocio están conectados de forma segura, con medidas de ciberseguridad que protegen las operaciones, los datos y el acceso remoto.",
    "Leverage the connected enterprise to accelerate innovation and advanced analytics.":
        "Aprovecha la empresa conectada para acelerar la innovación y el análisis avanzado.",

    # Intelligence levels
    "Production control": "Control de producción",
    "Production processes are digitally controlled and key operational data is generated automatically.":
        "Los procesos de producción se controlan digitalmente y los datos operativos clave se generan automáticamente.",
    "Operational visibility": "Visibilidad operativa",
    "Real-time visibility of operations, assets and production performance.":
        "Visibilidad en tiempo real de las operaciones, activos y desempeño de producción.",
    "Digital workflows": "Flujos de trabajo digitales",
    "Standard digital workflows trigger actions and follow-up.": "Los flujos de trabajo digitales estándar activan acciones y seguimiento.",
    "Data-driven decision making": "Toma de decisiones basada en datos",
    "Analytics support operational, tactical and strategic decision making.":
        "El análisis de datos respalda la toma de decisiones operativas, tácticas y estratégicas.",
    "Predictive intelligence": "Inteligencia predictiva",
    "AI and advanced analytics anticipate issues and recommend actions.":
        "La IA y el análisis avanzado anticipan problemas y recomiendan acciones.",
    "Expand AI-driven optimization and autonomous decision-making capabilities.":
        "Expande la optimización impulsada por IA y las capacidades de toma de decisiones autónoma.",

    # Solution value props
    "Identify obsolete assets and define a roadmap for modernization and risk reduction.":
        "Identifica activos obsoletos y define una hoja de ruta para su modernización y la reducción de riesgos.",
    "Understand where your factory stands against industry leaders and uncover the highest-value opportunities to accelerate your digital transformation.":
        "Entiende en qué posición se encuentra tu planta frente a los líderes de la industria y descubre las oportunidades de mayor valor para acelerar tu transformación digital.",
    "Define the long-term operational and digital transformation journey":
        "Define el camino de transformación operativa y digital a largo plazo.",
    "Develop workforce competence through structured training and certification programs.":
        "Desarrolla las competencias del personal mediante programas estructurados de capacitación y certificación.",
    "Deliver training and knowledge to employees anytime and anywhere.":
        "Entrega capacitación y conocimiento a los colaboradores en cualquier momento y lugar.",
    "Track workforce capabilities, identify skill gaps and support competency development.":
        "Da seguimiento a las capacidades del personal, identifica brechas de habilidades y apoya el desarrollo de competencias.",
    "Enable teams to share knowledge, solve problems faster and improve operational performance.":
        "Permite que los equipos compartan conocimiento, resuelvan problemas más rápido y mejoren el desempeño operativo.",
    "Gain rapid access to Tetra Pak experts to resolve issues faster and minimize production interruptions.":
        "Obtén acceso rápido a expertos de Tetra Pak para resolver problemas más rápido y minimizar interrupciones de producción.",
    "Digitize and standardize operating procedures to ensure consistent execution, reduce errors, and accelerate workforce onboarding.":
        "Digitaliza y estandariza los procedimientos operativos para garantizar una ejecución consistente, reducir errores y acelerar la incorporación de personal.",
    "Coordinate activities and ensure critical tasks are completed efficiently and consistently.":
        "Coordina actividades y garantiza que las tareas críticas se completen de forma eficiente y consistente.",
    "Capture, prioritize and resolve operational issues in a structured and collaborative way.":
        "Captura, prioriza y resuelve problemas operativos de forma estructurada y colaborativa.",
    "Enable operators to quickly identify, investigate and resolve production issues using alarms, event history and process playback.":
        "Permite a los operadores identificar, investigar y resolver rápidamente problemas de producción usando alarmas, historial de eventos y reproducción de procesos.",
    "Transform production data into actionable KPI reports that help teams identify losses, uncover root causes and prioritize continuous improvement opportunities.":
        "Transforma los datos de producción en reportes de KPI accionables que ayudan a los equipos a identificar pérdidas, descubrir causas raíz y priorizar oportunidades de mejora continua.",
    "Extend equipment lifetime and unlock new digital capabilities through automation upgrades.":
        "Extiende la vida útil de los equipos y desbloquea nuevas capacidades digitales mediante actualizaciones de automatización.",
    "Collect and contextualize data from all factory assets in a secure, scalable foundation that accelerates digital transformation and data-driven decision-making":
        "Recopila y contextualiza los datos de todos los activos de la planta en una base segura y escalable que acelera la transformación digital y la toma de decisiones basada en datos.",
    "A unified control solution for food & beverage factories, combining PLC & user experience standards for consistent automation and optimised decision quality":
        "Una solución de control unificada para plantas de alimentos y bebidas, que combina estándares de PLC y experiencia de usuario para una automatización consistente y decisiones de mayor calidad.",
    "Evaluate infrastructure risks and identify opportunities to improve reliability and security.":
        "Evalúa los riesgos de infraestructura e identifica oportunidades para mejorar la confiabilidad y la seguridad.",
    "Connect operational technology and business systems to create a seamless flow of data across the enterprise.":
        "Conecta la tecnología operativa y los sistemas de negocio para crear un flujo de datos fluido en toda la empresa.",
    "Secured infrastructure and ready to meet your production needs":
        "Infraestructura segura y lista para cubrir tus necesidades de producción.",
    "Improve operational visibility and decision-making through a modernized control environment.":
        "Mejora la visibilidad operativa y la toma de decisiones a través de un entorno de control modernizado.",
    "Connect production systems, equipment and business applications to improve visibility and decision making.":
        "Conecta los sistemas de producción, equipos y aplicaciones de negocio para mejorar la visibilidad y la toma de decisiones.",
    "Monitor production performance in real time to identify deviations early and enable faster, data-driven decisions.":
        "Monitorea el desempeño de producción en tiempo real para identificar desviaciones a tiempo y habilitar decisiones más rápidas basadas en datos.",
    "Provide complete traceability of materials, batches and process activities to support compliance, quality assurance and root cause analysis.":
        "Ofrece trazabilidad completa de materiales, lotes y actividades de proceso para apoyar el cumplimiento, el aseguramiento de calidad y el análisis de causa raíz.",
    "Capture and visualize the complete history of each production batch to improve traceability, process optimization and troubleshooting.":
        "Captura y visualiza el historial completo de cada lote de producción para mejorar la trazabilidad, la optimización de procesos y la resolución de problemas.",
    "Replace paper-based production records with trusted digital data for faster decisions and complete traceability.":
        "Reemplaza los registros de producción en papel con datos digitales confiables para decisiones más rápidas y trazabilidad completa.",
    "An end-to-end production solution connecting your business to your factory, creating a manufacturing plan & executing it with efficiency":
        "Una solución de producción integral que conecta tu negocio con tu planta, creando un plan de manufactura y ejecutándolo con eficiencia.",
    "Ensure traceability and efficient execution of materials across production from wherever you are in the factory":
        "Garantiza la trazabilidad y la ejecución eficiente de materiales en toda la producción desde cualquier punto de la planta.",
    "Digitize quality processes and gain real-time insights to improve product quality and compliance.":
        "Digitaliza los procesos de calidad y obtén información en tiempo real para mejorar la calidad del producto y el cumplimiento.",
    "Optimize cleaning operations to reduce costs, improve sustainability and maximize production availability.":
        "Optimiza las operaciones de limpieza para reducir costos, mejorar la sostenibilidad y maximizar la disponibilidad de producción.",
    "Consolidate quality data into actionable reports that improve compliance, product consistency and continuous improvement.":
        "Consolida los datos de calidad en reportes accionables que mejoran el cumplimiento, la consistencia del producto y la mejora continua.",
    "Provide contextualized factory data and insights to support faster and better decisions.":
        "Proporciona datos e información contextualizada de la planta para apoyar decisiones más rápidas y mejores.",
    "Integrated Real-Time Raw Material Reception Intelligence System for Food & Beverage Manufacturing":
        "Sistema inteligente integrado de recepción de materia prima en tiempo real para la manufactura de alimentos y bebidas.",
    "Optimize production plans and scheduling to maximize throughput and resource utilization.":
        "Optimiza los planes y la programación de producción para maximizar el rendimiento y el uso de recursos.",
    "Prevent failures before they occur and reduce unplanned downtime":
        "Previene fallas antes de que ocurran y reduce el tiempo de inactividad no planificado.",
    "Improve yield, quality and operational efficiency in cheese production processes.":
        "Mejora el rendimiento, la calidad y la eficiencia operativa en los procesos de producción de queso.",

    # Profiles (complementary text)
    "Your factory is in the foundational stage of its automation and digital transformation journey.":
        "Tu planta está en la etapa fundacional de su transformación digital y de automatización.",
    "Your factory has established key digital capabilities and is ready to scale data-driven operations.":
        "Tu planta ha establecido capacidades digitales clave y está lista para escalar operaciones basadas en datos.",
    "Your factory has a strong digital foundation and can focus on optimization and business value realization.":
        "Tu planta tiene una base digital sólida y puede enfocarse en la optimización y la generación de valor de negocio.",
    "Your factory is positioned to accelerate innovation and advanced analytics.":
        "Tu planta está posicionada para acelerar la innovación y el análisis avanzado.",
}

# Tie-break order when two dimensions share the same score (highest wins the
# tie, i.e. is treated as "less urgent" and pushed later in the ranking) —
# per spec: Strategy > Operational Excellence > Connectivity > People > Intelligence.
DIMENSION_PRIORITY: dict[str, int] = {
    "strategy": 5,
    "operations": 4,
    "connectivity": 3,
    "people": 2,
    "intelligence": 1,
}

# Dimension-wide fallback solutions, used when the target level has no
# solutions mapped in the framework sheet for that specific level.
FALLBACK_SOLUTIONS: dict[str, list[str]] = {
    "strategy": ["Automation & Digital benchmarking", "Automation & Digital transformation assessment"],
    "people": ["Connected Workforce Collaboration", "Workforce Skills Management"],
    "operations": ["Digital Standard Operating Procedures", "Digital Task management", "Digital Issue management"],
    "connectivity": ["OT Infrastructure Assessment", "Smart manufacturing infrastructure"],
    "intelligence": ["Production Management", "Quality Management", "KPI reports"],
}

# Which dimensions each MVS-savings KPI is considered to depend on. The
# workbook's "MVS potential savings" sheet gives one improvement range per
# industry sub-sector without tying it to a specific dimension, so this
# mapping is our own reasonable assumption (documented here rather than
# buried in app logic): OEE and quality losses are primarily driven by
# operational discipline and intelligence/analytics maturity; energy waste
# by operational and connectivity (metering/visibility) maturity; stock
# turnover by connectivity (data flow) and intelligence (planning) maturity.
KPI_DIMENSIONS: dict[str, list[str]] = {
    "oee": ["operations", "intelligence"],
    "quality": ["operations", "intelligence"],
    "energy": ["operations", "connectivity"],
    "stock": ["connectivity", "intelligence"],
}


def translate_fw(lang: str, text: str) -> str:
    """Translate a workbook-sourced string. Falls back to the original
    English text (never crashes) if lang == 'en' or no translation exists."""
    if not text:
        return text
    if lang == "en":
        return text
    return _ES_LOOKUP.get(text.strip(), text)


# ---------------------------------------------------------------------------
# Static UI strings
# ---------------------------------------------------------------------------
UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "At 10,000 Feet: How Ready Are You for Intelligent Transition?",
        "intro1": (
            "This self-diagnostic helps you understand how prepared your operation is "
            "for **intelligent automation**. In a few minutes you'll rate your maturity "
            "across five dimensions and receive a normalized profile, your overall "
            "readiness level, and a personalized roadmap of next moves."
        ),
        "pillars_prefix": "The five dimensions are: ",
        "step_answer": "Answer",
        "step_calculate": "Calculate",
        "step_review": "Review",
        "tell_us": "Tell us about you",
        "full_name": "Name *",
        "work_email": "Email *",
        "email_help": "Use the same email you registered with for the forum.",
        "company": "Company *",
        "food_category": "Food Category *",
        "invalid_email": "Please enter a valid email address.",
        "next": "Next →",
        "motivation_question": "What is your biggest motivation to advance in the intelligent transition?",
        "motivation_optional": "(optional)",
        "motivation_placeholder": "Write your answer here...",
        "continue": "Continue",
        "back": "← Back",
        "step_of": "Step {step} of {total}",
        "dont_know": "I don't know / I don't want to rate this dimension",
        "level0_label": "Don't know / Skip",
        "level0_note": "This dimension will be excluded from the chart, MVS comparison and recommendations.",
        "level_label": "Maturity Level",
        "calc_score": "See My Results",
        "results_for": "Results for {name} — {company}",
        "tab_overview": "Overview",
        "tab_reco": "Recommendations",
        "tab_stories": "Customer Stories",
        "radar_title": "#### Your Current State vs. Industry Minimum Viable Status (MVS)",
        "series_current": "Your Current State",
        "series_mvs": "Industry MVS",
        "not_assessed_note": "Dimensions marked as \"I don't know\" are excluded from the chart and calculations.",
        "mvs_info_title": "ℹ️ What is the Minimum Viable Status (MVS)?",
        "mvs_info_body": (
            "A World Economic Forum benchmark defining the minimum maturity level needed "
            "to remain competitive in your industry."
        ),
        "savings_title": "#### Potential Improvement Opportunity from Reaching MVS",
        "savings_caption": "Indicative estimates for **{category}** segment:",
        "savings_kpi_col": "KPI",
        "savings_value_col": "Potential Improvement to Reach MVS",
        "already_at_mvs": "Already at or above MVS",
        "not_assessed_kpi": "Not assessed — excluded",
        "reco_title": "### Top Recommended Improvement Areas & Solutions",
        "reco_need_assessment": "Rate at least one dimension to see recommendations.",
        "reco_level_transition": "Level {current} → Level {target}",
        "reco_mastered_title": "You've reached Level 5 — Next step",
        "solutions_none": "No specific solutions mapped yet for this level — check back soon.",
        "factory_os_badge": "Factory OS",
        "stories_title": "### Customer Success Stories",
        "stories_context": "Since your recommended next step is in **{dimension}**, check out this success story:",
        "stories_none": "No specific case studies found for your recommended dimensions yet.",
        "read_story": "Read Full Story →",
        "start_over": "Start Over",
        "dev_warning": (
            "⚠️ Dev mode: Google Sheets not configured. "
            "Submissions are being written to `{csv}`."
        ),
        "live_title": "🛫 Live Results — At 10,000 Feet",
        "live_count": "{count} submissions so far · refreshes automatically",
        "live_empty": "No submissions yet. This view refreshes automatically as people complete the assessment.",
        "email_consent_note": "📧 We'll email your results to the address above.",
        "email_subject": "Your At 10,000 Feet results are ready 🛫",
        "email_greeting": "Hi {name},",
        "email_intro": "Thanks for completing the assessment! Here's a summary of your results.",
        "email_dimensions_title": "Your maturity by dimension",
        "email_recommendations_title": "Your top recommended next steps",
        "email_footer": "This email was sent automatically because you completed the At 10,000 Feet assessment at Foro MX 2026.",
    },
    "es": {
        "title": "A 10,000 Pies: ¿Qué Tan Listo Estás para la Transición Inteligente?",
        "intro1": (
            "Este autodiagnóstico te ayuda a entender qué tan preparada está tu operación "
            "para la **automatización inteligente**. En unos minutos calificarás tu madurez "
            "en cinco dimensiones y recibirás un perfil normalizado, tu nivel de "
            "preparación general y una hoja de ruta personalizada de próximos pasos."
        ),
        "pillars_prefix": "Las cinco dimensiones son: ",
        "step_answer": "Responder",
        "step_calculate": "Calcular",
        "step_review": "Revisar",
        "tell_us": "Cuéntanos sobre ti",
        "full_name": "Nombre *",
        "work_email": "Correo electrónico *",
        "email_help": "Usa el mismo correo con el que te registraste al foro.",
        "company": "Empresa *",
        "food_category": "Categoría de Alimento *",
        "invalid_email": "Por favor ingresa un correo electrónico válido.",
        "next": "Siguiente →",
        "motivation_question": "¿Cuál es tu mayor motivación para avanzar en la transición inteligente?",
        "motivation_optional": "(opcional)",
        "motivation_placeholder": "Escribe tu respuesta aquí...",
        "continue": "Continuar",
        "back": "← Atrás",
        "step_of": "Paso {step} de {total}",
        "dont_know": "No sé / no quiero calificar esta dimensión",
        "level0_label": "No sé / Omitir",
        "level0_note": "Esta dimensión se excluirá de la gráfica, la comparación con el MVS y las recomendaciones.",
        "level_label": "Nivel de Madurez",
        "calc_score": "Ver Mis Resultados",
        "results_for": "Resultados para {name} — {company}",
        "tab_overview": "Resumen",
        "tab_reco": "Recomendaciones",
        "tab_stories": "Casos de Éxito",
        "radar_title": "#### Tu Estado Actual vs. Estado Mínimo Viable de la Industria (MVS)",
        "series_current": "Tu Estado Actual",
        "series_mvs": "MVS de la Industria",
        "not_assessed_note": "Las dimensiones marcadas como \"No sé\" se excluyen de la gráfica y los cálculos.",
        "mvs_info_title": "ℹ️ ¿Qué es el Estado Mínimo Viable (MVS)?",
        "mvs_info_body": (
            "Un referente del Foro Económico Mundial que define el nivel mínimo de madurez "
            "necesario para mantenerte competitivo en tu industria."
        ),
        "savings_title": "#### Oportunidad de Mejora Potencial al Alcanzar el MVS",
        "savings_caption": "Estimaciones indicativas para el segmento **{category}**:",
        "savings_kpi_col": "KPI",
        "savings_value_col": "Mejora Potencial para Alcanzar el MVS",
        "already_at_mvs": "Ya alcanzaste o superaste el MVS",
        "not_assessed_kpi": "No evaluado — excluido",
        "reco_title": "### Principales Áreas de Mejora y Soluciones Recomendadas",
        "reco_need_assessment": "Califica al menos una dimensión para ver recomendaciones.",
        "reco_level_transition": "Nivel {current} → Nivel {target}",
        "reco_mastered_title": "Alcanzaste el Nivel 5 — Próximo paso",
        "solutions_none": "Aún no hay soluciones específicas mapeadas para este nivel.",
        "factory_os_badge": "Factory OS",
        "stories_title": "### Casos de Éxito de Clientes",
        "stories_context": "Ya que tu próximo paso recomendado es en **{dimension}**, conoce este caso de éxito:",
        "stories_none": "Aún no encontramos casos de éxito específicos para tus dimensiones recomendadas.",
        "read_story": "Leer Caso Completo →",
        "start_over": "Comenzar de Nuevo",
        "dev_warning": (
            "⚠️ Modo desarrollo: Google Sheets no está configurado. "
            "Los envíos se están guardando en `{csv}`."
        ),
        "live_title": "🛫 Resultados en Vivo — At 10,000 Feet",
        "live_count": "{count} respuestas hasta ahora · se actualiza automáticamente",
        "live_empty": "Aún no hay respuestas. Esta vista se actualiza automáticamente conforme la gente completa la evaluación.",
        "email_consent_note": "📧 Enviaremos tus resultados al correo indicado arriba.",
        "email_subject": "Tus resultados de At 10,000 Feet ya están listos 🛫",
        "email_greeting": "Hola {name},",
        "email_intro": "¡Gracias por completar la evaluación! Aquí tienes un resumen de tus resultados.",
        "email_dimensions_title": "Tu madurez por dimensión",
        "email_recommendations_title": "Tus principales próximos pasos recomendados",
        "email_footer": "Este correo se envió automáticamente porque completaste la evaluación At 10,000 Feet en Foro MX 2026.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = UI[lang][key]
    return text.format(**kwargs) if kwargs else text
