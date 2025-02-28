import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const MCQAssessmentScreen = ({ navigation, route }) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  // Get MCQs from params and transform them to the required format
  const { generatedMCQs = [] } = route.params || {};
  
  // Format the MCQs to include options (combining answer + distractors)
  const [mcqs, setMcqs] = useState([]);
  
  useEffect(() => {
    if (generatedMCQs && generatedMCQs.length > 0) {
      // Transform data format to what the assessment screen expects
      const formattedMcqs = generatedMCQs.map(mcq => ({
        question: mcq.question,
        options: [mcq.answer, ...mcq.distractors], // Combine correct answer with distractors
        correctAnswer: mcq.answer
      }));
      
      // Shuffle options for each question
      const shuffledMcqs = formattedMcqs.map(mcq => {
        const shuffledOptions = [...mcq.options].sort(() => 0.5 - Math.random());
        return {
          ...mcq,
          options: shuffledOptions
        };
      });
      
      setMcqs(shuffledMcqs);
    }
  }, [generatedMCQs]);

  const handleAnswer = (questionIndex, selectedOption) => {
    setSelectedAnswers({
      ...selectedAnswers,
      [questionIndex]: selectedOption
    });
  };

  const handleSubmit = () => {
    if (Object.keys(selectedAnswers).length < mcqs.length) {
      Alert.alert(
        'Incomplete',
        'Please answer all questions before submitting.',
        [{ text: 'OK' }]
      );
      return;
    }

    const score = mcqs.reduce((acc, mcq, index) => {
      return acc + (selectedAnswers[index] === mcq.correctAnswer ? 1 : 0);
    }, 0);

    navigation.navigate('MCQResult', {
      score,
      total: mcqs.length,
      results: mcqs.map((mcq, index) => ({
        ...mcq,
        userAnswer: selectedAnswers[index]
      }))
    });
  };

  if (mcqs.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.noContent}>No MCQs for assessment.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.questionCard}>
        <Text style={styles.questionNumber}>
          Question {currentQuestion + 1} of {mcqs.length}
        </Text>
        <Text style={styles.questionText}>
          {mcqs[currentQuestion].question}
        </Text>

        <View style={styles.optionsContainer}>
          {mcqs[currentQuestion].options.map((option, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.optionButton,
                selectedAnswers[currentQuestion] === option && styles.selectedOption
              ]}
              onPress={() => handleAnswer(currentQuestion, option)}
            >
              <Text style={[
                styles.optionText,
                selectedAnswers[currentQuestion] === option && styles.selectedOptionText
              ]}>
                {option}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.navigationButtons}>
        <TouchableOpacity
          style={[styles.navButton, currentQuestion === 0 && styles.disabledButton]}
          disabled={currentQuestion === 0}
          onPress={() => setCurrentQuestion(curr => curr - 1)}
        >
          <Ionicons name="chevron-back" size={24} color="#fff" />
          <Text style={styles.navButtonText}>Previous</Text>
        </TouchableOpacity>

        {currentQuestion === mcqs.length - 1 ? (
          <TouchableOpacity
            style={styles.submitButton}
            onPress={handleSubmit}
          >
            <Text style={styles.submitButtonText}>Submit</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.navButton}
            onPress={() => setCurrentQuestion(curr => curr + 1)}
          >
            <Text style={styles.navButtonText}>Next</Text>
            <Ionicons name="chevron-forward" size={24} color="#fff" />
          </TouchableOpacity>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  noContent: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: 16,
    color: '#666',
  },
  questionCard: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 16,
    borderRadius: 8,
    elevation: 3,
  },
  questionNumber: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 8,
  },
  questionText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  optionsContainer: {
    gap: 10,
  },
  optionButton: {
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  selectedOption: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  optionText: {
    fontSize: 16,
  },
  selectedOptionText: {
    color: '#fff',
  },
  navigationButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
  },
  navButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    padding: 10,
    borderRadius: 10,
    minWidth: 100,
    justifyContent: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  navButtonText: {
    color: '#fff',
    fontSize: 16,
    marginHorizontal: 5,
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    padding: 10,
    borderRadius: 10,
    minWidth: 100,
    alignItems: 'center',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 10,
    borderRadius: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    marginRight: 5,
  },
});

export default MCQAssessmentScreen;