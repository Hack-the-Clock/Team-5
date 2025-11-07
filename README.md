AI Code Quality Evaluator

Step 1: Create Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  


Step 2: Install Dependencies**

pip install -r requirements.txt


Step 3: Set API Key

export GROQ_API_KEY="your_groq_api_key_here" in .env file

Step 4: Start the Application
python3 api.py & python3 -m http.server 8080


Alternatively:

If the website doesn't load, you can just do:python3 hackathon.py  as well
Video explanation for the code: https://gmuedu-my.sharepoint.com/:v:/g/personal/j20_gmu_edu/EWuDH8LNLkpElRDXtpYkp_EBvv8Wy8Bnz9tGo2Nq9mGz-g?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=HXnGVX

# Credits and Attributions

## External APIs and Services

### Groq API
- **Purpose**: Large Language Model for code generation
- **URL**: https://groq.com
- **License**: Commercial API service
- **Usage**: Code generation via llama-3.3-70b-versatile model

### Pyodide
- **Purpose**: Python runtime for WebAssembly
- **URL**: https://pyodide.org
- **License**: Mozilla Public License 2.0
- **Usage**: Browser-based Python code execution and analysis
- **CDN**: https://cdn.jsdelivr.net/pyodide/v0.24.0/full/

## Python Libraries

### Flask
- **Purpose**: Web framework for REST API
- **URL**: https://flask.palletsprojects.com
- **License**: BSD-3-Clause
- **Version**: 3.0.0+

### Flask-CORS
- **Purpose**: Cross-Origin Resource Sharing support
- **URL**: https://flask-cors.readthedocs.io
- **License**: MIT
- **Version**: 4.0.0+

### Groq Python SDK
- **Purpose**: Python client for Groq API
- **URL**: https://github.com/groq/groq-python
- **License**: Apache 2.0
- **Version**: 0.9.0+

### Radon
- **Purpose**: Code metrics and complexity analysis
- **URL**: https://radon.readthedocs.io
- **License**: MIT
- **Version**: 6.0.1+
- **Usage**: Cyclomatic complexity, Halstead metrics, maintainability index

### Bandit
- **Purpose**: Security vulnerability scanning for Python
- **URL**: https://bandit.readthedocs.io
- **License**: Apache 2.0
- **Version**: 1.7.5+
- **Usage**: Static security analysis

## Fonts

### Inter
- **Source**: Google Fonts
- **URL**: https://fonts.google.com/specimen/Inter
- **License**: SIL Open Font License 1.1
- **Designer**: Rasmus Andersson

### JetBrains Mono
- **Source**: Google Fonts
- **URL**: https://fonts.google.com/specimen/JetBrains+Mono
- **License**: SIL Open Font License 1.1
- **Designer**: JetBrains

## Development Tools and References

### Python AST Module
- **Purpose**: Abstract Syntax Tree parsing
- **Documentation**: https://docs.python.org/3/library/ast.html
- **License**: Python Software Foundation License
- **Usage**: Code structure analysis

### MDN Web Docs
- **Purpose**: Reference for HTML/CSS/JavaScript
- **URL**: https://developer.mozilla.org
- **License**: CC0 1.0 Universal

## Methodologies and Concepts

### SOLID Principles
- **Reference**: Object-oriented design principles
- **Original Author**: Robert C. Martin
- **Usage**: Code quality assessment for Single Responsibility Principle

### Cyclomatic Complexity
- **Reference**: Software metric for code complexity
- **Original Author**: Thomas J. McCabe (1976)
- **Usage**: Code complexity scoring

### Maintainability Index
- **Reference**: Software maintainability metric
- **Original Paper**: Oman & Hagemeister (1992)
- **Usage**: Code maintainability scoring

### Halstead Complexity Measures
- **Reference**: Software science metrics
- **Original Author**: Maurice Howard Halstead (1977)
- **Usage**: Code volume and complexity analysis

## Original Work

All custom implementations, algorithms, and user interface designs in this project are original work created by the development team. The scoring algorithms, iterative refinement system, and evaluation methodology are custom implementations not derived from any external sources.

## License Compliance

This project uses various open-source libraries and follows their respective licenses. All dependencies are listed in `requirements.txt` and used in accordance with their license terms.
