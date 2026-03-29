import google.generativeai as genai
from config import apikey, model_name

def test_model():
    print(f"Testing Gemini API with model: {model_name}")
    genai.configure(api_key=apikey)
    try:
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content("Hello, this is a test.")
        print(f"Response success: {response.text}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == '__main__':
    test_model()
    except Exception as e:
        import traceback
        print(f"FAILED: {e}\n{traceback.format_exc()}")
        return False

if __name__ == '__main__':
    test_model()
