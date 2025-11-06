"""
Multi-Language Code Analysis Support

Provides code analysis for multiple programming languages:
- Python: Full analysis (Radon, Bandit, AST)
- C/C++: Static analysis (Cppcheck, Clang-Tidy)
- Java: Static analysis (Checkstyle, PMD, SpotBugs)
- Others: LLM-based analysis

External Dependencies:
- Groq API (https://groq.com) - LLM analysis for unsupported languages
- Cppcheck (GPL-3.0) - C/C++ static analysis
- Checkstyle (LGPL-2.1) - Java code style checker
- PMD (Apache-2.0) - Java source code analyzer

See CREDITS.md for full attribution.
"""

import os
import re
import tempfile
import subprocess
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


LANGUAGE_EXTENSIONS = {
    'python': ['.py'],
    'java': ['.java'],
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h', '.hh'],
    'javascript': ['.js', '.jsx'],
    'typescript': ['.ts', '.tsx'],
    'go': ['.go'],
    'rust': ['.rs'],
    'csharp': ['.cs'],
    'ruby': ['.rb'],
    'php': ['.php'],
}


def detect_language(code: str, filename: str = None) -> str:
    """
    Detect programming language from code content or filename.
    """
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return lang
    
    # Content-based detection
    if re.search(r'^(def|class|import|from)\s+', code, re.MULTILINE):
        return 'python'
    elif re.search(r'^(public|private|protected)\s+(class|interface|enum)', code, re.MULTILINE):
        return 'java'
    elif re.search(r'#include\s+<', code):
        if '.cpp' in (filename or '') or 'namespace' in code or 'class' in code:
            return 'cpp'
        return 'c'
    elif re.search(r'^(function|const|let|var|class)\s+', code, re.MULTILINE):
        if 'interface' in code or ': string' in code or ': number' in code:
            return 'typescript'
        return 'javascript'
    elif re.search(r'^package\s+main|^func\s+', code, re.MULTILINE):
        return 'go'
    elif re.search(r'^(fn|pub|struct|impl)\s+', code, re.MULTILINE):
        return 'rust'
    elif re.search(r'^namespace\s+|using\s+System', code, re.MULTILINE):
        return 'csharp'
    
    return 'unknown'


def analyze_c_cpp_code(code: str, language: str = 'cpp') -> dict:
    """
    Analyze C/C++ code using cppcheck static analyzer.
    
    Cppcheck: GPL-3.0 License
    See: http://cppcheck.sourceforge.net/
    """
    result = {
        'syntax_ok': True,
        'language': language,
        'security_issues': 0,
        'style_issues': 0,
        'performance_issues': 0,
        'warnings': [],
        'errors': [],
        'tool': 'cppcheck',
        'error': None
    }
    
    try:
        # Check if cppcheck is installed
        try:
            subprocess.run(['cppcheck', '--version'], 
                         capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            result['error'] = 'cppcheck not installed. Install: brew install cppcheck (macOS) or apt-get install cppcheck (Linux)'
            return result
        
        # Create temporary file
        suffix = '.cpp' if language == 'cpp' else '.c'
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run cppcheck
            cmd = [
                'cppcheck',
                '--enable=all',
                '--suppress=missingIncludeSystem',
                '--xml',
                '--xml-version=2',
                temp_file
            ]
            
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse XML output (errors go to stderr)
            output = proc.stderr
            
            # Count issues by severity
            result['errors'] = re.findall(r'severity="error"[^>]*msg="([^"]+)"', output)
            result['warnings'] = re.findall(r'severity="warning"[^>]*msg="([^"]+)"', output)
            result['security_issues'] = len(re.findall(r'severity="(error|warning)"[^>]*id="(buffer|memory|null|leak)', output))
            result['style_issues'] = len(re.findall(r'severity="style"', output))
            result['performance_issues'] = len(re.findall(r'severity="performance"', output))
            
            result['syntax_ok'] = len(result['errors']) == 0
            
        finally:
            os.unlink(temp_file)
            
    except subprocess.TimeoutExpired:
        result['error'] = 'Analysis timeout (>30s)'
    except Exception as e:
        result['error'] = f'Analysis failed: {str(e)}'
    
    return result


def analyze_java_code(code: str) -> dict:
    """
    Analyze Java code using basic syntax and pattern checks.
    Full analysis requires Checkstyle/PMD which need configuration files.
    """
    result = {
        'syntax_ok': True,
        'language': 'java',
        'classes': 0,
        'methods': 0,
        'has_main': False,
        'has_javadoc': False,
        'imports': 0,
        'potential_issues': [],
        'tool': 'basic_java_analyzer',
        'error': None
    }
    
    try:
        # Count classes
        result['classes'] = len(re.findall(r'\b(public|private|protected)?\s*class\s+\w+', code))
        
        # Count methods
        result['methods'] = len(re.findall(r'\b(public|private|protected|static)\s+\w+\s+\w+\s*\([^)]*\)', code))
        
        # Check for main method
        result['has_main'] = bool(re.search(r'public\s+static\s+void\s+main\s*\(', code))
        
        # Check for JavaDoc
        result['has_javadoc'] = bool(re.search(r'/\*\*[^*]*\*+([^/*][^*]*\*+)*/', code))
        
        # Count imports
        result['imports'] = len(re.findall(r'^import\s+', code, re.MULTILINE))
        
        # Basic syntax check
        if not re.search(r'class\s+\w+', code):
            result['syntax_ok'] = False
            result['potential_issues'].append('No class definition found')
        
        # Check for common issues
        if re.search(r'System\.out\.print', code):
            result['potential_issues'].append('Uses System.out.print (prefer logging framework)')
        
        if re.search(r'catch\s*\(\s*Exception\s+\w+\s*\)\s*\{?\s*\}', code):
            result['potential_issues'].append('Empty catch block found')
        
        if not re.search(r'package\s+', code):
            result['potential_issues'].append('No package declaration')
            
    except Exception as e:
        result['error'] = f'Analysis failed: {str(e)}'
    
    return result


def analyze_with_llm(code: str, language: str) -> dict:
    """
    Use LLM to analyze code in languages without dedicated static analyzers.
    """
    if not client:
        return {
            'syntax_ok': None,
            'language': language,
            'analysis': 'LLM analysis unavailable (no API key)',
            'error': 'GROQ_API_KEY not configured'
        }
    
    try:
        prompt = f"""Analyze this {language} code for quality and issues. Provide a JSON response with:
- syntax_ok: boolean (is syntax valid?)
- complexity_estimate: string (low/medium/high)
- security_concerns: list of potential security issues
- style_issues: list of code style problems
- best_practices: list of violated best practices
- recommendations: list of improvement suggestions

Code to analyze:
```{language}
{code}
```

Respond ONLY with valid JSON, no markdown."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are an expert {language} code reviewer. Analyze code and respond with JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        
        analysis_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        if '```json' in analysis_text:
            analysis_text = analysis_text.split('```json')[1].split('```')[0].strip()
        elif '```' in analysis_text:
            analysis_text = analysis_text.split('```')[1].split('```')[0].strip()
        
        analysis = json.loads(analysis_text)
        analysis['language'] = language
        analysis['tool'] = 'llm_analysis'
        
        return analysis
        
    except json.JSONDecodeError:
        return {
            'syntax_ok': None,
            'language': language,
            'analysis': analysis_text,
            'tool': 'llm_analysis',
            'error': 'Failed to parse LLM response as JSON'
        }
    except Exception as e:
        return {
            'syntax_ok': None,
            'language': language,
            'error': f'LLM analysis failed: {str(e)}',
            'tool': 'llm_analysis'
        }


def analyze_code_multi_language(code: str, language: str = None, filename: str = None) -> dict:
    """
    Main entry point for multi-language code analysis.
    Routes to appropriate analyzer based on language.
    """
    if not language:
        language = detect_language(code, filename)
    
    result = {
        'detected_language': language,
        'analysis': None,
        'analyzer_used': None
    }
    
    if language == 'python':
        # Use existing Python analysis
        result['analyzer_used'] = 'python_full_stack'
        result['note'] = 'Use evaluate_code() from hackathon.py for Python'
        
    elif language == 'c':
        result['analyzer_used'] = 'cppcheck'
        result['analysis'] = analyze_c_cpp_code(code, 'c')
        
    elif language == 'cpp':
        result['analyzer_used'] = 'cppcheck'
        result['analysis'] = analyze_c_cpp_code(code, 'cpp')
        
    elif language == 'java':
        result['analyzer_used'] = 'basic_java + llm'
        basic_analysis = analyze_java_code(code)
        llm_analysis = analyze_with_llm(code, 'java')
        result['analysis'] = {
            'basic': basic_analysis,
            'llm': llm_analysis
        }
        
    else:
        result['analyzer_used'] = 'llm_only'
        result['analysis'] = analyze_with_llm(code, language)
    
    return result


def generate_code_multi_language(prompt: str, language: str = 'python') -> str:
    """
    Generate code in specified language using LLM.
    """
    if not client:
        return f"// API key not configured\n// Fallback {language} code"
    
    lang_configs = {
        'python': {
            'expert': 'Python',
            'practices': 'type hints, docstrings, error handling, unit tests',
            'marker': 'python'
        },
        'java': {
            'expert': 'Java',
            'practices': 'JavaDoc, proper exception handling, JUnit tests, SOLID principles',
            'marker': 'java'
        },
        'c': {
            'expert': 'C',
            'practices': 'proper memory management, error checking, header guards, documentation',
            'marker': 'c'
        },
        'cpp': {
            'expert': 'C++',
            'practices': 'RAII, smart pointers, const correctness, proper destructors, modern C++ features',
            'marker': 'cpp'
        },
        'javascript': {
            'expert': 'JavaScript',
            'practices': 'async/await, error handling, JSDoc comments, modern ES6+ syntax',
            'marker': 'javascript'
        },
        'typescript': {
            'expert': 'TypeScript',
            'practices': 'strict types, interfaces, proper error handling, async/await',
            'marker': 'typescript'
        }
    }
    
    config = lang_configs.get(language, {
        'expert': language,
        'practices': 'best practices and clean code',
        'marker': language
    })
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"""You are an expert {config['expert']} developer who writes production-ready code with:
- {config['practices']}
- Security best practices
- Clean, maintainable code structure
- Comprehensive error handling

Return ONLY the {language} code without markdown formatting or explanations."""},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        
        code = response.choices[0].message.content
        
        # Strip markdown code blocks
        marker = config['marker']
        if f"```{marker}" in code:
            code = code.split(f"```{marker}")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        
        return code
        
    except Exception as e:
        return f"// Code generation failed: {str(e)}"
