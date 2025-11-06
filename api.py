"""
Flask API for AI Code Quality Evaluator
Provides endpoints for code generation and evaluation

External Dependencies:
- Flask (BSD-3-Clause): https://flask.palletsprojects.com
- Flask-CORS (MIT): https://flask-cors.readthedocs.io
- See CREDITS.md for full attribution
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()
from hackathon import (
    generate_code,
    evaluate_code,
    calculate_production_score,
    generate_recommendations,
    refine_code_automatic
)

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "AI Code Quality Evaluator API is running",
        "api_key_set": bool(GROQ_API_KEY)
    })


@app.route('/api/generate', methods=['POST'])
def generate_code_endpoint():
    """
    Generate code from a prompt
    
    Request body:
    {
        "prompt": "Create a REST API for user authentication"
    }
    
    Response:
    {
        "code": "generated Python code",
        "evaluation": { ... },
        "production_score": { ... },
        "recommendations": [ ... ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "Missing 'prompt' in request body"}), 400
        
        prompt = data['prompt'].strip()
        
        if not prompt:
            return jsonify({"error": "Prompt cannot be empty"}), 400
        
        # Generate code
        print(f"Generating code for prompt: {prompt[:100]}...")
        generated_code = generate_code(prompt)
        
        # Evaluate the generated code
        print("Evaluating generated code...")
        eval_results = evaluate_code(generated_code)
        
        # Calculate production score
        prod_score = calculate_production_score(eval_results)
        
        # Generate recommendations
        recommendations = generate_recommendations(eval_results)
        
        return jsonify({
            "success": True,
            "code": generated_code,
            "evaluation": eval_results,
            "production_score": prod_score,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error in generate endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/evaluate', methods=['POST'])
def evaluate_code_endpoint():
    """
    Evaluate existing Python code
    
    Request body:
    {
        "code": "Python code to evaluate"
    }
    
    Response:
    {
        "evaluation": { ... },
        "production_score": { ... },
        "recommendations": [ ... ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({"error": "Missing 'code' in request body"}), 400
        
        code = data['code'].strip()
        
        if not code:
            return jsonify({"error": "Code cannot be empty"}), 400
        
        # Evaluate the Python code
        print("Evaluating Python code...")
        eval_results = evaluate_code(code)
        prod_score = calculate_production_score(eval_results)
        recommendations = generate_recommendations(eval_results)
        
        return jsonify({
            "success": True,
            "evaluation": eval_results,
            "production_score": prod_score,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error in evaluate endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
        # Generate recommendations
        recommendations = generate_recommendations(eval_results)
        
        return jsonify({
            "success": True,
            "evaluation": eval_results,
            "production_score": prod_score,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error in evaluate endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/improve', methods=['POST'])
def improve_code_endpoint():
    """
    Apply iterative improvements to Python code based on test results and recommendations
    
    Request body:
    {
        "prompt": "Original task description",
        "code": "Python code to improve",
        "max_iterations": 8  // optional, default 8
    }
    
    Response:
    {
        "success": true,
        "original_code": "...",
        "improved_code": "...",
        "original_score": {...},
        "final_score": {...},
        "iterations": 3,
        "improvement_history": [...],
        "recommendations_applied": [...],
        "recommendations": [...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({"error": "Missing 'code' in request body"}), 400
        
        code = data['code'].strip()
        prompt = data.get('prompt', 'Improve this code').strip()
        max_iterations = data.get('max_iterations', 8)
        
        if not code:
            return jsonify({"error": "Code cannot be empty"}), 400
        
        print(f"\n{'='*60}")
        print(f"IMPROVEMENT REQUEST")
        print(f"{'='*60}")
        print(f"Improving Python code (max {max_iterations} iterations)...")
        
        # Evaluate original code and get recommendations
        original_eval = evaluate_code(code)
        original_score = calculate_production_score(original_eval)
        original_recommendations = generate_recommendations(original_eval)
        
        print(f"\nOriginal Score: {original_score['total_score']}/100")
        print(f"Original Recommendations: {len(original_recommendations)}")
        for i, rec in enumerate(original_recommendations[:5], 1):
            print(f"  {i}. {rec[:80]}...")
        
        # Apply improvements based on recommendations
        print(f"\n🤖 Starting AI-powered improvements based on recommendations...")
        improved_code, final_eval, iterations, history = refine_code_automatic(
            prompt, code, original_eval
        )
        
        final_score = calculate_production_score(final_eval)
        final_recommendations = generate_recommendations(final_eval)
        
        print(f"\n{'='*60}")
        print(f"IMPROVEMENT COMPLETE")
        print(f"{'='*60}")
        print(f"Final Score: {final_score['total_score']}/100")
        print(f"Improvement: +{final_score['total_score'] - original_score['total_score']} points")
        print(f"Iterations: {iterations}")
        print(f"Remaining Recommendations: {len(final_recommendations)}")
        print(f"{'='*60}\n")
        
        return jsonify({
            "success": True,
            "original_code": code,
            "improved_code": improved_code,
            "original_score": original_score,
            "original_evaluation": original_eval,
            "final_score": final_score,
            "final_evaluation": final_eval,
            "iterations": iterations,
            "improvement_history": history,
            "recommendations_applied": original_recommendations,  # Recommendations that were addressed
            "recommendations": final_recommendations  # Remaining recommendations
        })
        
    except Exception as e:
        print(f"Error in improve endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("="*60)
    print("AI Code Quality Evaluator API")
    print("="*60)
    print(f"API Key set: {bool(GROQ_API_KEY)}")
    print("\nEndpoints:")
    print("  GET  /api/health    - Health check")
    print("  POST /api/generate  - Generate code from prompt")
    print("  POST /api/evaluate  - Evaluate existing code")
    print("  POST /api/improve   - Apply iterative improvements")
    print("\nStarting server on http://localhost:5001")
    print("Access from browser at: http://localhost:5001")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
