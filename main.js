/**
 * AI Code Quality Evaluator - Frontend JavaScript
 * 
 * External Dependencies:
 * - Pyodide (MPL 2.0): https://pyodide.org - Browser Python runtime
 * 
 * See CREDITS.md for full attribution.
 */

let pyodideReady = null;

const API_BASE_URL = 'http://localhost:5001/api';

async function initPyodideAndAdapter() {
  const pyodide = await loadPyodide({ 
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.0/full/" 
  });
  
  const resp = await fetch("pyodide_adapter.py");
  const pyCode = await resp.text();
  pyodide.runPython(pyCode);
  
  return pyodide;
}

async function analyzeInBrowser(code) {
  if (!pyodideReady) pyodideReady = initPyodideAndAdapter();
  const pyodide = await pyodideReady;
  
  const analyze = pyodide.globals.get("analyze_code_simple");
  const jsonStr = analyze(code);
  const jsStr = jsonStr.toString();
  
  try { 
    analyze.destroy && analyze.destroy(); 
  } catch(e) {}
  
  return JSON.parse(jsStr);
}

async function checkAPIHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (response.ok) {
      const data = await response.json();
      return data.status === 'healthy';
    }
    return false;
  } catch (error) {
    return false;
  }
}

async function generateCodeFromAPI(prompt) {
  const response = await fetch(`${API_BASE_URL}/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to generate code');
  }
  
  return await response.json();
}

async function evaluateCodeFromAPI(code) {
  const response = await fetch(`${API_BASE_URL}/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to evaluate code');
  }
  
  return await response.json();
}

async function improveCodeFromAPI(code, prompt = 'Improve this code', maxIterations = 3) {
  const response = await fetch(`${API_BASE_URL}/improve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      code, 
      prompt,
      max_iterations: maxIterations
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to improve code');
  }
  
  return await response.json();
}

function calculateProductionScore(evalResults) {
  let score = 0;
  const breakdown = {};

  if (!evalResults.syntax_ok) {
    return { 
      total_score: 0, 
      rating: "Not Ready", 
      percentage: 0,
      breakdown: { syntax: 0 } 
    };
  }

  breakdown.syntax = 20;
  score += 20;

  if (evalResults.has_docstrings) {
    breakdown.documentation = 15;
    score += 15;
  } else {
    breakdown.documentation = 0;
  }

  const complexity = evalResults.avg_complexity || 0;
  if (complexity <= 5) {
    breakdown.complexity = 15;
    score += 15;
  } else if (complexity <= 10) {
    breakdown.complexity = 10;
    score += 10;
  } else {
    breakdown.complexity = Math.max(0, 15 - (complexity - 10));
    score += breakdown.complexity;
  }

  const securityIssues = evalResults.security?.security_issues || 0;
  if (securityIssues === 0) {
    breakdown.security = 20;
    score += 20;
  } else {
    breakdown.security = Math.max(0, 20 - (securityIssues * 5));
    score += breakdown.security;
  }

  let errScore = 0;
  const errHandling = evalResults.error_handling || {};
  if (errHandling.has_try_except) errScore += 4;
  if (errHandling.bare_except_count === 0) errScore += 2;
  if (errHandling.has_logging) errScore += 2;
  if (errHandling.has_validation) errScore += 2;
  breakdown.error_handling = errScore;
  score += errScore;

  const tests = evalResults.test_coverage || {};
  if (tests.has_tests && tests.assertion_count > 0) {
    breakdown.tests = 10;
    score += 10;
  } else {
    breakdown.tests = 0;
  }

  const mi = evalResults.maintainability?.maintainability_index || 0;
  if (mi > 85) {
    breakdown.maintainability = 10;
    score += 10;
  } else if (mi > 65) {
    breakdown.maintainability = 7;
    score += 7;
  } else if (mi > 40) {
    breakdown.maintainability = 4;
    score += 4;
  } else {
    breakdown.maintainability = 0;
  }

  let rating;
  if (score >= 85) rating = "Production Ready";
  else if (score >= 70) rating = "Nearly Ready";
  else if (score >= 50) rating = "Needs Work";
  else rating = "Not Ready";

  return {
    total_score: score,
    max_score: 100,
    percentage: Math.round((score / 100) * 100),
    rating: rating,
    breakdown: breakdown
  };
}

function generateRecommendations(evalResults) {
  const recommendations = [];

  if (!evalResults.has_docstrings) {
    recommendations.push("Add docstrings to all functions and classes for better documentation");
  }
  if ((evalResults.avg_complexity || 0) > 10) {
    recommendations.push("Refactor complex functions to reduce cyclomatic complexity (target < 10)");
  }
  if (evalResults.security?.high_severity > 0) {
    recommendations.push("Fix high-severity security vulnerabilities immediately");
  }
  if (!evalResults.error_handling?.has_try_except) {
    recommendations.push("Add proper error handling with try-except blocks");
  }
  if (!evalResults.test_coverage?.has_tests) {
    recommendations.push("Implement unit tests with assertions for better code reliability");
  }
  if ((evalResults.maintainability?.maintainability_index || 100) < 65) {
    recommendations.push("Improve code maintainability by adding comments and reducing complexity");
  }
  if (!evalResults.error_handling?.has_validation) {
    recommendations.push("Add input validation to improve code robustness");
  }
  if ((evalResults.error_handling?.bare_except_count || 0) > 0) {
    recommendations.push("Replace bare except clauses with specific exception types");
  }
  if (!evalResults.error_handling?.has_logging) {
    recommendations.push("Implement logging for better debugging and monitoring");
  }

  return recommendations;
}

function renderProductionScore(prodScore) {
  const scoreValue = document.getElementById('scoreValue');
  const scorePercentage = document.getElementById('scorePercentage');
  const scoreRating = document.getElementById('scoreRating');
  const scoreRing = document.getElementById('scoreRing');

  let currentScore = 0;
  const targetScore = prodScore.total_score;
  const increment = targetScore / 50;
  
  const scoreAnimation = setInterval(() => {
    currentScore += increment;
    if (currentScore >= targetScore) {
      currentScore = targetScore;
      clearInterval(scoreAnimation);
    }
    scoreValue.textContent = Math.round(currentScore);
  }, 20);

  scorePercentage.textContent = `${prodScore.percentage}%`;
  scoreRating.textContent = prodScore.rating;
  
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (prodScore.percentage / 100) * circumference;
  scoreRing.style.strokeDashoffset = offset;

  const ratingColors = {
    'Production Ready': '#059669',
    'Nearly Ready': '#10b981',
    'Needs Work': '#f59e0b',
    'Not Ready': '#ef4444'
  };
  scoreRing.style.stroke = ratingColors[prodScore.rating] || '#0ea5e9';
}

function renderScoreBreakdown(breakdown) {
  const container = document.getElementById('scoreBreakdown');
  container.innerHTML = '';

  const maxScores = {
    syntax: 20,
    documentation: 15,
    complexity: 15,
    security: 20,
    error_handling: 10,
    tests: 10,
    maintainability: 10
  };

  Object.entries(breakdown).forEach(([category, score]) => {
    const maxScore = maxScores[category] || 10;
    const percentage = (score / maxScore) * 100;
    
    let ratingClass = 'poor';
    if (percentage >= 90) ratingClass = 'excellent';
    else if (percentage >= 70) ratingClass = 'good';
    else if (percentage >= 50) ratingClass = 'moderate';

    const item = document.createElement('div');
    item.className = `breakdown-item ${ratingClass}`;
    item.innerHTML = `
      <div class="breakdown-header">
        <span class="breakdown-label">${category.replace('_', ' ')}</span>
        <span class="breakdown-score">${score}/${maxScore}</span>
      </div>
      <div class="breakdown-bar">
        <div class="breakdown-bar-fill" style="width: ${percentage}%"></div>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderMetricCard(containerId, items) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  items.forEach(({ label, value, status }) => {
    const item = document.createElement('div');
    item.className = 'metric-item';
    item.innerHTML = `
      <span class="metric-label">${label}</span>
      <span class="metric-value ${status || ''}">${value}</span>
    `;
    container.appendChild(item);
  });
}

function renderRecommendations(recommendations) {
  const container = document.getElementById('recommendationsList');
  container.innerHTML = '';

  if (recommendations.length === 0) {
    container.innerHTML = `
      <div class="no-recommendations">
        <span>No major recommendations. Code follows best practices.</span>
      </div>
    `;
    return;
  }

  // Add header explaining recommendations
  const header = document.createElement('div');
  header.className = 'recommendations-header';
  header.innerHTML = `
    <p style="margin-bottom: 15px; color: #64748b; font-size: 0.95rem;">
       Based on the test results, here are <strong>${recommendations.length}</strong> recommendation(s) to improve your code. 
      Click <strong>"Improve Code"</strong> below to have our AI automatically apply these improvements.
    </p>
  `;
  container.appendChild(header);

  recommendations.forEach((rec, index) => {
    const item = document.createElement('div');
    item.className = 'recommendation-item';
    
    // Determine priority based on keywords
    let priority = 'medium';
    let priorityIcon = '!!';
    if (rec.toLowerCase().includes('critical') || rec.toLowerCase().includes('security') || rec.toLowerCase().includes('high-severity')) {
      priority = 'high';
      priorityIcon = '!!!';
    } else if (rec.toLowerCase().includes('add') || rec.toLowerCase().includes('implement')) {
      priority = 'low';
      priorityIcon = '!';
    }
    
    item.innerHTML = `
      <div class="recommendation-content">
        <span class="recommendation-priority-icon">${priorityIcon}</span>
        <span class="recommendation-text"><strong>${index + 1}.</strong> ${rec}</span>
      </div>
    `;
    item.dataset.priority = priority;
    container.appendChild(item);
  });
}

function displayResults(evalResults, code) {
  currentLanguage = 'python'; // Track current language
  const prodScore = calculateProductionScore(evalResults);
  const recommendations = generateRecommendations(evalResults);

  document.getElementById('loadingState').classList.add('hidden');
  document.getElementById('resultsSection').classList.remove('hidden');

  renderProductionScore(prodScore);
  renderScoreBreakdown(prodScore.breakdown);

  renderMetricCard('basicMetrics', [
    { label: 'Syntax Valid', value: evalResults.syntax_ok ? 'Yes' : 'No', status: evalResults.syntax_ok ? 'success' : 'danger' },
    { label: 'Functions', value: evalResults.functions || 0 },
    { label: 'Avg Complexity', value: (evalResults.avg_complexity || 0).toFixed(1), status: (evalResults.avg_complexity || 0) <= 5 ? 'success' : (evalResults.avg_complexity || 0) <= 10 ? 'warning' : 'danger' },
    { label: 'Has Docstrings', value: evalResults.has_docstrings ? 'Yes' : 'No', status: evalResults.has_docstrings ? 'success' : 'warning' }
  ]);

  const sec = evalResults.security || {};
  renderMetricCard('securityMetrics', [
    { label: 'Total Issues', value: sec.security_issues || 0, status: (sec.security_issues || 0) === 0 ? 'success' : 'warning' },
    { label: 'High Severity', value: sec.high_severity || 0, status: (sec.high_severity || 0) === 0 ? 'success' : 'danger' },
    { label: 'Status', value: sec.error ? 'Scanner unavailable' : (sec.security_issues || 0) === 0 ? 'Secure' : 'Issues found', status: sec.error ? '' : (sec.security_issues || 0) === 0 ? 'success' : 'warning' }
  ]);

  // Render error handling metrics
  const err = evalResults.error_handling || {};
  renderMetricCard('errorHandlingMetrics', [
    { label: 'Try-Except Blocks', value: err.exception_count || 0, status: (err.exception_count || 0) > 0 ? 'success' : 'warning' },
    { label: 'Bare Except Clauses', value: err.bare_except_count || 0, status: (err.bare_except_count || 0) === 0 ? 'success' : 'danger' },
    { label: 'Has Logging', value: err.has_logging ? 'Yes' : 'No', status: err.has_logging ? 'success' : 'warning' },
    { label: 'Input Validation', value: err.has_validation ? 'Yes' : 'No', status: err.has_validation ? 'success' : 'warning' }
  ]);

  // Render test metrics
  const tests = evalResults.test_coverage || {};
  renderMetricCard('testMetrics', [
    { label: 'Has Tests', value: tests.has_tests ? 'Yes' : 'No', status: tests.has_tests ? 'success' : 'danger' },
    { label: 'Test Functions', value: tests.test_functions || 0, status: (tests.test_functions || 0) > 0 ? 'success' : 'warning' },
    { label: 'Assertions', value: tests.assertion_count || 0, status: (tests.assertion_count || 0) > 0 ? 'success' : 'warning' },
    { label: 'Frameworks', value: tests.test_frameworks?.join(', ') || 'None' }
  ]);

  // Render maintainability metrics
  const mi = evalResults.maintainability || {};
  renderMetricCard('maintainabilityMetrics', [
    { label: 'MI Score', value: (mi.maintainability_index || 0).toFixed(1), status: (mi.maintainability_index || 0) > 85 ? 'success' : (mi.maintainability_index || 0) > 65 ? 'warning' : 'danger' },
    { label: 'Rating', value: mi.rating || 'N/A' },
    { label: 'Halstead Volume', value: (mi.halstead_volume || 0).toFixed(1) },
    { label: 'Logical LOC', value: mi.lloc || 0 }
  ]);

  // Render SOLID metrics
  const solid = evalResults.solid_principles || {};
  renderMetricCard('solidMetrics', [
    { label: 'SRP Score', value: `${(solid.srp_score || 0).toFixed(1)}/100`, status: (solid.srp_score || 0) > 80 ? 'success' : (solid.srp_score || 0) > 60 ? 'warning' : 'danger' },
    { label: 'Classes', value: solid.class_count || 0 },
    { label: 'Avg Methods/Class', value: (solid.avg_methods_per_class || 0).toFixed(1) },
    { label: 'God Classes', value: solid.god_classes?.join(', ') || 'None', status: (solid.god_classes?.length || 0) === 0 ? 'success' : 'warning' }
  ]);

  // Render recommendations
  renderRecommendations(recommendations);

  document.querySelector('#evaluatedCode code').textContent = code;

  document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.addEventListener("DOMContentLoaded", () => {
  const codeInput = document.getElementById('codeInput');
  const promptInput = document.getElementById('promptInput');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const loadExampleBtn = document.getElementById('loadExampleBtn');
  const copyCodeBtn = document.getElementById('copyCodeBtn');
  const toggleBtns = document.querySelectorAll('.toggle-btn');
  const pasteMode = document.getElementById('pasteMode');
  const generateMode = document.getElementById('generateMode');

  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.mode;
      
      toggleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      if (mode === 'paste') {
        pasteMode.classList.add('active');
        generateMode.classList.remove('active');
        analyzeBtn.innerHTML = 'Evaluate Code Quality';
        analyzeBtn.classList.remove('btn-warning');
      } else {
        pasteMode.classList.remove('active');
        generateMode.classList.add('active');
        analyzeBtn.innerHTML = ' Generate & Evaluate Code';
        analyzeBtn.classList.add('btn-warning');
        
        checkBackendStatus();
      }
    });
  });

  async function checkBackendStatus() {
    const statusEl = document.getElementById('backendStatus');
    const indicator = statusEl.querySelector('.status-indicator');
    const statusText = statusEl.querySelector('.status-text');
    const notice = document.getElementById('backendNotice');
    
    indicator.className = 'status-indicator checking';
    statusText.textContent = 'Checking backend connection...';
    
    const isHealthy = await checkAPIHealth();
    
    if (isHealthy) {
      indicator.className = 'status-indicator connected';
      statusText.textContent = '✓ Backend connected and ready';
      notice.classList.add('collapsed');
    } else {
      indicator.className = 'status-indicator disconnected';
      statusText.textContent = '⚠ Backend not available - setup required';
      notice.classList.remove('collapsed');
    }
  }

  const toggleNoticeBtn = document.getElementById('toggleNotice');
  const backendNotice = document.getElementById('backendNotice');
  
  if (toggleNoticeBtn) {
    toggleNoticeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      backendNotice.classList.toggle('collapsed');
      toggleNoticeBtn.textContent = backendNotice.classList.contains('collapsed') 
        ? 'Show Details' 
        : 'Hide Details';
    });
  }

  loadExampleBtn.addEventListener('click', () => {
    codeInput.value = `def calculate_factorial(n):
    """Calculate factorial of a number with error handling."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

class Calculator:
    """Simple calculator with basic operations."""
    
    def add(self, a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a, b):
        """Divide a by b with error handling."""
        try:
            return a / b
        except ZeroDivisionError:
            raise ValueError("Cannot divide by zero")

# Test functions
def test_factorial():
    """Test factorial calculation."""
    assert calculate_factorial(5) == 120
    assert calculate_factorial(0) == 1
    
def test_calculator():
    """Test calculator operations."""
    calc = Calculator()
    assert calc.add(2, 3) == 5
    assert calc.subtract(5, 3) == 2`;

    document.querySelector('[data-mode="paste"]').click();
  });

  analyzeBtn.addEventListener('click', async () => {
    const activeMode = document.querySelector('.toggle-btn.active').dataset.mode;

    if (activeMode === 'paste') {
      const code = codeInput.value.trim();
      
      if (!code) {
        alert('Please paste some Python code to evaluate.');
        return;
      }

      const apiHealthy = await checkAPIHealth();
      
      document.getElementById('resultsSection').classList.add('hidden');
      const loadingState = document.getElementById('loadingState');
      loadingState.classList.remove('hidden');

      try {
        let evalResults;
        
        if (apiHealthy) {
          loadingState.querySelector('.loading-text').textContent = 'Analyzing Python code quality and production readiness...';
          loadingState.querySelector('.loading-subtext').textContent = 'Evaluating syntax, security, maintainability, and best practices';
          
          const response = await evaluateCodeFromAPI(code);
          evalResults = response.evaluation;
        } else {
          loadingState.querySelector('.loading-text').textContent = 'Analyzing code in browser...';
          loadingState.querySelector('.loading-subtext').textContent = 'Limited analysis (API offline). Start API server for full evaluation.';
          
          evalResults = await analyzeInBrowser(code);
        }
        
        displayResults(evalResults, code);
      } catch (err) {
        document.getElementById('loadingState').classList.add('hidden');
        loadingState.querySelector('.loading-text').textContent = 'Analyzing code quality and production readiness...';
        loadingState.querySelector('.loading-subtext').textContent = 'Evaluating syntax, security, maintainability, and best practices';
        
        alert(`Analysis failed: ${err.message}`);
        console.error(err);
      }
    } else {
      const prompt = promptInput.value.trim();
      
      if (!prompt) {
        alert('Please describe what you want to build.');
        return;
      }

      const apiHealthy = await checkAPIHealth();
      if (!apiHealthy) {
        if (confirm(' Backend API Not Available\n\nThe code generation backend is not running.\n\nWould you like to see setup instructions?\n\nClick OK to see instructions, or Cancel to continue.')) {
          alert(' Setup Instructions:\n\n1. Install dependencies:\n   pip install flask flask-cors groq radon bandit\n\n2. Set API key:\n   export GROQ_API_KEY="your_key"\n\n3. Start the API server:\n   python api.py\n\n4. The server will run on http://localhost:5001\n\nThen try generating code again!');
        }
        return;
      }

      document.getElementById('resultsSection').classList.add('hidden');
      const loadingState = document.getElementById('loadingState');
      loadingState.classList.remove('hidden');
      loadingState.querySelector('.loading-text').textContent = 'Generating Python code with AI...';
      loadingState.querySelector('.loading-subtext').textContent = 'This may take 10-20 seconds. Groq is creating production-ready code for you.';

      try {
        const response = await generateCodeFromAPI(prompt);
        
        if (response.success) {
          const evalResults = response.evaluation;
          const code = response.code;
          
          loadingState.querySelector('.loading-text').textContent = 'Analyzing code quality and production readiness...';
          loadingState.querySelector('.loading-subtext').textContent = 'Evaluating syntax, security, maintainability, and best practices';
          
          displayResults(evalResults, code);
        } else {
          throw new Error(response.error || 'Code generation failed');
        }
      } catch (err) {
        document.getElementById('loadingState').classList.add('hidden');
        loadingState.querySelector('.loading-text').textContent = 'Analyzing code quality and production readiness...';
        loadingState.querySelector('.loading-subtext').textContent = 'Evaluating syntax, security, maintainability, and best practices';
        
        alert(`Code generation failed: ${err.message}\n\nMake sure the API server is running:\npython api.py`);
        console.error(err);
      }
    }
  });

  copyCodeBtn.addEventListener('click', () => {
    const code = document.querySelector('#evaluatedCode code').textContent;
    navigator.clipboard.writeText(code).then(() => {
      const originalText = copyCodeBtn.innerHTML;
      copyCodeBtn.innerHTML = '<span>✓ Copied!</span>';
      setTimeout(() => {
        copyCodeBtn.innerHTML = originalText;
      }, 2000);
    });
  });

  const improveCodeBtn = document.getElementById('improveCodeBtn');
  improveCodeBtn.addEventListener('click', async () => {
    const code = document.querySelector('#evaluatedCode code').textContent;
    if (!code || code.trim() === '') {
      alert('No code to improve. Please evaluate code first.');
      return;
    }

    const apiHealthy = await checkAPIHealth();
    if (!apiHealthy) {
      alert('Backend API is required for code improvement.\n\nPlease ensure the API server is running:\npython3 api.py');
      return;
    }

    const improvementProgress = document.getElementById('improvementProgress');
    const improvementResults = document.getElementById('improvementResults');
    
    // Update progress message to explain what's happening
    const progressText = improvementProgress.querySelector('.progress-text');
    const progressDetails = improvementProgress.querySelector('.progress-details');
    
    progressText.textContent = 'Analyzing recommendations and applying improvements...';
    progressDetails.innerHTML = '<span style="color: #64748b;">Our AI is automatically fixing the issues identified in the evaluation</span>';
    
    improvementProgress.classList.remove('hidden');
    improvementResults.classList.add('hidden');
    improveCodeBtn.disabled = true;

    try {
      const response = await improveCodeFromAPI(code, 'Improve this code for production readiness', 3);
      
      if (response.success) {
        improvementProgress.classList.add('hidden');
        improvementResults.classList.remove('hidden');
        
        const originalScore = response.original_score.total_score;
        const finalScore = response.final_score.total_score;
        const gain = finalScore - originalScore;
        
        document.getElementById('originalScoreValue').textContent = originalScore;
        document.getElementById('improvedScoreValue').textContent = finalScore;
        document.getElementById('scoreGainValue').textContent = gain >= 0 ? `+${gain}` : gain;
        
        // Show iterations and which recommendations were applied
        const iterationsInfo = document.getElementById('iterationsPerformed');
        iterationsInfo.innerHTML = `
           ${response.iterations} iteration${response.iterations !== 1 ? 's' : ''} performed<br>
          <span style="font-size: 0.9rem; color: #64748b;">Applied ${response.recommendations?.length || 0} recommendation(s) from the evaluation</span>
        `;
        
        // Update the main evaluation results to show the improved code's metrics
        displayResults(response.final_evaluation, response.improved_code);
        
        // Update the production score with improved score
        renderProductionScore(response.final_score);
        
        // Update recommendations with new recommendations for the improved code
        if (response.recommendations && response.recommendations.length > 0) {
          renderRecommendations(response.recommendations);
        } else {
          // Show success message if no more recommendations
          const recContainer = document.getElementById('recommendationsList');
          recContainer.innerHTML = `
            <div class="no-recommendations" style="background: #ecfdf5; border: 1px solid #86efac; color: #065f46;">
              <span> Excellent! All recommendations have been applied. Your code is production-ready!</span>
            </div>
          `;
        }
        
        // Always show the improved code section
        const evaluatedCodePre = document.getElementById('evaluatedCode');
        let improvedCodeSection = document.getElementById('improvedCodeSection');
        
        if (!improvedCodeSection) {
          improvedCodeSection = document.createElement('div');
          improvedCodeSection.id = 'improvedCodeSection';
          improvedCodeSection.style.marginTop = '20px';
          improvedCodeSection.innerHTML = `
            <div class="code-display-header">
              <h3>✨ Improved Code (Score: ${finalScore}/100)</h3>
              <button id="copyImprovedCodeBtn" class="btn-icon-only" title="Copy improved code">
                <span>Copy</span>
              </button>
            </div>
            <div style="padding: 12px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; margin-bottom: 12px;">
              <p style="margin: 0; font-size: 0.9rem; color: #065f46;">
                <strong>Auto-Improvements Applied:</strong> The AI has automatically addressed the identified issues 
                based on test results and evaluation metrics.
              </p>
            </div>
            <pre id="improvedCode" class="code-display"><code></code></pre>
          `;
          evaluatedCodePre.parentNode.insertBefore(improvedCodeSection, evaluatedCodePre.nextSibling);
          
          // Add copy button handler for improved code
          document.getElementById('copyImprovedCodeBtn').addEventListener('click', () => {
            const improvedCode = document.querySelector('#improvedCode code').textContent;
            navigator.clipboard.writeText(improvedCode).then(() => {
              const btn = document.getElementById('copyImprovedCodeBtn');
              const originalText = btn.innerHTML;
              btn.innerHTML = '<span>✓ Copied!</span>';
              setTimeout(() => {
                btn.innerHTML = originalText;
              }, 2000);
            });
          });
        } else {
          // Update the header with new score
          const header = improvedCodeSection.querySelector('h3');
          if (header) {
            header.textContent = `Improved Code (Score: ${finalScore}/100)`;
          }
        }
        
        // Set the improved code
        document.querySelector('#improvedCode code').textContent = response.improved_code;
        
        // Scroll to the improved code section
        setTimeout(() => {
          improvedCodeSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 500);
        
        // Show success message
        if (gain > 0) {
          setTimeout(() => {
            alert(`Code Improved Successfully!\n\n` +
                  `Score improved from ${originalScore} to ${finalScore} (+${gain} points)\n\n` +
                  `The AI has automatically applied the recommendations from your evaluation.`);
          }, 1000);
        }
      } else {
        throw new Error(response.error || 'Improvement failed');
      }
    } catch (err) {
      improvementProgress.classList.add('hidden');
      alert(`Code improvement failed: ${err.message}\n\nMake sure the API server is running with a valid Groq API key.`);
      console.error(err);
    } finally {
      improveCodeBtn.disabled = false;
      // Reset progress text
      progressText.textContent = 'Applying iterative improvements...';
      progressDetails.innerHTML = '<span id="improvementIteration">Iteration 1/3</span><span id="improvementScore">Score: 0 → 0</span>';
    }
  });
});
