import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { generateResultReport } from '../utils/pdfGenerator';

const MCQResultScreen = ({ navigation, route }) => {
  const { score = 0, total = 0, results = [] } = route.params || {};
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;

  let grade = 'F';
  if (percentage >= 90) grade = 'A';
  else if (percentage >= 80) grade = 'B';
  else if (percentage >= 70) grade = 'C';
  else if (percentage >= 60) grade = 'D';

  const handleDownloadReport = () => {
    Alert.alert(
      'Download Report',
      'Choose a format to download your assessment report',
      [
        {
          text: 'PDF',
          onPress: () => generateResultReport(results, score, total, 'pdf')
        },
        {
          text: 'Text File',
          onPress: () => generateResultReport(results, score, total, 'txt')
        },
        {
          text: 'Cancel',
          style: 'cancel'
        }
      ]
    );
  };

  // Add a share/export function
  const handleExport = async (format = 'pdf') => {
    try {
      await generateResultReport(results, score, total, format);
    } catch (error) {
      console.error('Error exporting results:', error);
      Alert.alert('Error', 'Failed to export results. Please try again.');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.scoreCard}>
        <Text style={styles.grade}>Grade: {grade}</Text>
        <Text style={styles.score}>{score}/{total}</Text>
        <Text style={[
          styles.percentage, 
          percentage >= 70 ? styles.goodScore : styles.badScore
        ]}>
          {percentage}%
        </Text>
      </View>

      <View style={styles.resultsContainer}>
        <Text style={styles.sectionTitle}>Detailed Results</Text>
        {results.map((result, index) => (
          <View key={index} style={styles.questionCard}>
            <Text style={styles.questionText}>
              {index + 1}. {result.question}
            </Text>
            <View style={styles.answersContainer}>
              <Text style={styles.answerLabel}>Your Answer:</Text>
              <Text style={[
                styles.answer,
                result.userAnswer === result.correctAnswer
                  ? styles.correctAnswer
                  : styles.wrongAnswer
              ]}>
                {result.userAnswer}
              </Text>
              {result.userAnswer !== result.correctAnswer && (
                <>
                  <Text style={styles.answerLabel}>Correct Answer:</Text>
                  <Text style={[styles.answer, styles.correctAnswer]}>
                    {result.correctAnswer}
                  </Text>
                </>
              )}
            </View>
          </View>
        ))}
      </View>

      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={styles.homeButton}
          onPress={() => navigation.navigate('Home')}
        >
          <Ionicons name="home" size={24} color="#fff" />
          <Text style={styles.homeButtonText}>Back to Home</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.downloadButton}
          onPress={handleDownloadReport}
        >
          <Ionicons name="download-outline" size={24} color="#fff" />
          <Text style={styles.downloadButtonText}>Download Report</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scoreCard: {
    backgroundColor: '#f8f9fa',
    padding: 20,
    margin: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  grade: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 10,
  },
  score: {
    fontSize: 48,
    fontWeight: 'bold',
  },
  percentage: {
    fontSize: 20,
    marginTop: 5,
  },
  goodScore: {
    color: 'green',
  },
  badScore: {
    color: '#ff6b6b',
  },
  resultsContainer: {
    padding: 15,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  questionCard: {
    backgroundColor: '#f8f9fa',
    padding: 15,
    marginBottom: 12,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  questionText: {
    fontSize: 16,
    marginBottom: 10,
  },
  answersContainer: {
    marginLeft: 10,
  },
  answerLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  answer: {
    fontSize: 16,
    marginBottom: 10,
    paddingLeft: 10,
    borderLeftWidth: 2,
    paddingBottom: 5,
  },
  correctAnswer: {
    borderLeftColor: 'green',
    color: 'green',
  },
  wrongAnswer: {
    borderLeftColor: '#ff6b6b',
    color: '#ff6b6b',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 15,
    marginBottom: 20,
  },
  homeButton: {
    backgroundColor: '#007AFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    flex: 1,
    marginRight: 8,
  },
  homeButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  downloadButton: {
    backgroundColor: '#4CAF50',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    flex: 1,
    marginLeft: 8,
  },
  downloadButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});

export default MCQResultScreen;
