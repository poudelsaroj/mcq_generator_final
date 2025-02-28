// utils/apiService.js
const API_BASE_URL = 'http://192.168.1.16:8000'; // Update with your actual API URL

export const generateMCQsFromAPI = async (content, numQuestions) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/generate-mcqs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        context: content,
        num_questions: numQuestions
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to generate MCQs');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const generateAssessmentFromAPI = async (content, numQuestions) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/generate-assessment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        context: content,
        num_questions: numQuestions
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to generate assessment');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};