import * as FileSystem from 'expo-file-system';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { Platform, Alert } from 'react-native';
import { sampleMCQs } from '../data/sampleMCQs';

// Updated to accept MCQs directly instead of a category
export const generateMCQFile = async (mcqs, format = 'pdf', title = "Generated MCQs") => {
  try {
    if (!mcqs || mcqs.length === 0) {
      Alert.alert('Error', 'No MCQs to download');
      return false;
    }

    const timestamp = new Date().getTime();
    let fileUri;

    // Transform mcqs format if needed (from question, answer, distractors to question, options, correctAnswer)
    const formattedMcqs = mcqs.map(mcq => {
      return {
        question: mcq.question,
        options: [mcq.answer, ...mcq.distractors], // Combine answer and distractors as options
        correctAnswer: mcq.answer
      };
    });

    if (format === 'pdf') {
      // Generate PDF content with styling
      const htmlContent = `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <title>MCQ Questions</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 20px; }
              .header { text-align: center; margin-bottom: 30px; }
              .question { 
                margin-bottom: 20px; 
                padding: 15px;
                background-color: #f8f9fa;
                border-left: 4px solid #007AFF;
              }
              .options { margin-left: 20px; }
              .answer-key { 
                margin-top: 30px;
                border-top: 2px dashed #007AFF;
                padding-top: 20px;
              }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>Multiple Choice Questions</h1>
              <h2>${title.toUpperCase()}</h2>
            </div>

            ${formattedMcqs.map((mcq, index) => `
              <div class="question">
                <p><strong>Question ${index + 1}:</strong> ${mcq.question}</p>
                <div class="options">
                  ${mcq.options.map((option, optIndex) => `
                    <p>${String.fromCharCode(65 + optIndex)}. ${option}</p>
                  `).join('')}
                </div>
              </div>
            `).join('')}

            <div class="answer-key">
              <h2>Answer Key</h2>
              ${formattedMcqs.map((mcq, index) => `
                <p><strong>Question ${index + 1}:</strong> ${mcq.correctAnswer}</p>
              `).join('')}
            </div>
          </body>
        </html>
      `;

      const file = await Print.printToFileAsync({
        html: htmlContent,
        base64: false
      });
      fileUri = file.uri;

    } else {
      // Generate TXT content
      const textContent = `
MCQ Questions
=================================

${formattedMcqs.map((mcq, index) => `
Question ${index + 1}: ${mcq.question}

Options:
${mcq.options.map((option, optIndex) => `${String.fromCharCode(65 + optIndex)}. ${option}`).join('\n')}
`).join('\n\n')}

Answer Key
==========
${formattedMcqs.map((mcq, index) => `Question ${index + 1}: ${mcq.correctAnswer}`).join('\n')}
`;

      fileUri = `${FileSystem.documentDirectory}mcq_${timestamp}.txt`;
      await FileSystem.writeAsStringAsync(fileUri, textContent);
    }

    const isAvailable = await Sharing.isAvailableAsync();
    if (isAvailable) {
      await Sharing.shareAsync(fileUri, {
        mimeType: format === 'pdf' ? 'application/pdf' : 'text/plain',
        dialogTitle: `Download MCQ Questions (${format.toUpperCase()})`,
        UTI: format === 'pdf' ? 'com.adobe.pdf' : 'public.text'
      });
      return true;
    } else {
      Alert.alert('Error', 'Sharing is not available on this device');
      return false;
    }

  } catch (error) {
    console.error('Error generating file:', error);
    Alert.alert('Error', 'Failed to generate file. Please try again.');
    return false;
  }
};

// New function for generating assessment reports
export const generateResultReport = async (results, score, total, format = 'pdf') => {
  try {
    let fileUri;
    const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
    let grade = 'F';
    if (percentage >= 90) grade = 'A';
    else if (percentage >= 80) grade = 'B';
    else if (percentage >= 70) grade = 'C';
    else if (percentage >= 60) grade = 'D';
    
    if (format === 'pdf') {
      // Generate PDF HTML content
      const htmlContent = `
        <!DOCTYPE html>
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no" />
            <style>
              body { 
                font-family: system-ui, -apple-system, sans-serif;
                margin: 0;
                padding: 20px;
                color: #333;
              }
              .header {
                text-align: center;
                margin-bottom: 30px;
              }
              .score-card {
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                border: 2px solid #007AFF;
                border-radius: 10px;
                background-color: #f8f9fa;
              }
              .grade {
                font-size: 24px;
                font-weight: bold;
                color: #007AFF;
              }
              .score {
                font-size: 48px;
                font-weight: bold;
                margin: 10px 0;
              }
              .percentage {
                font-size: 20px;
                margin-top: 10px;
              }
              .good-score {
                color: green;
              }
              .bad-score {
                color: #ff6b6b;
              }
              .question {
                padding: 15px;
                margin-bottom: 15px;
                background-color: #f8f9fa;
                border-left: 4px solid #007AFF;
                border-radius: 5px;
              }
              .question-text {
                font-weight: bold;
                margin-bottom: 10px;
              }
              .user-answer {
                margin: 5px 0;
                padding-left: 10px;
              }
              .correct {
                color: green;
                border-left: 3px solid green;
                padding-left: 8px;
              }
              .incorrect {
                color: #ff6b6b;
                border-left: 3px solid #ff6b6b;
                padding-left: 8px;
              }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>Assessment Results</h1>
              <div class="score-card">
                <p class="grade">Grade: ${grade}</p>
                <p class="score">${score}/${total}</p>
                <p class="percentage ${percentage >= 70 ? 'good-score' : 'bad-score'}">${percentage}%</p>
              </div>
            </div>

            <h2>Detailed Results</h2>
            
            ${results.map((result, index) => `
              <div class="question">
                <p class="question-text">${index + 1}. ${result.question}</p>
                <div>
                  <p>Your Answer:</p>
                  <p class="user-answer ${result.userAnswer === result.correctAnswer ? 'correct' : 'incorrect'}">
                    ${result.userAnswer}
                  </p>
                  ${result.userAnswer !== result.correctAnswer ? `
                    <p>Correct Answer:</p>
                    <p class="user-answer correct">${result.correctAnswer}</p>
                  ` : ''}
                </div>
              </div>
            `).join('')}
          </body>
        </html>
      `;

      const file = await Print.printToFileAsync({
        html: htmlContent,
        base64: false
      });
      fileUri = file.uri;

    } else {
      // Generate text content for the report
      const textContent = `
ASSESSMENT RESULTS
=================

Grade: ${grade}
Score: ${score}/${total}
Percentage: ${percentage}%

DETAILED RESULTS
===============

${results.map((result, index) => `
Question ${index + 1}: ${result.question}
Your Answer: ${result.userAnswer} ${result.userAnswer === result.correctAnswer ? '(Correct)' : '(Incorrect)'}
${result.userAnswer !== result.correctAnswer ? `Correct Answer: ${result.correctAnswer}` : ''}
`).join('\n')}
`;

      // Create a text file
      const fileName = `MCQ_Assessment_Results_${new Date().toISOString().split('T')[0]}.txt`;
      fileUri = `${FileSystem.documentDirectory}${fileName}`;
      await FileSystem.writeAsStringAsync(fileUri, textContent);
    }

    // Share the file
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(fileUri);
    } else {
      Alert.alert(
        'Sharing not available',
        'Sharing is not available on your device'
      );
    }
  } catch (error) {
    console.error('Error generating assessment report:', error);
    Alert.alert('Error', 'Failed to generate assessment report');
  }
};