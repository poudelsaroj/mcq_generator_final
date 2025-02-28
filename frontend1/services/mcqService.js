// services/mcqService.js
import { generateMCQsFromAPI, generateAssessmentFromAPI } from '../utils/apiService';

export const generateMCQs = async (text, numQuestions) => {
  try {
    const response = await generateMCQsFromAPI(text, numQuestions);
    return response.questions || [];
  } catch (error) {
    console.error('Error generating MCQs:', error);
    throw error;
  }
};

export const generateAssessment = async (text, numQuestions) => {
  try {
    const response = await generateAssessmentFromAPI(text, numQuestions);
    return response.questions || [];
  } catch (error) {
    console.error('Error generating assessment:', error);
    throw error;
  }
};