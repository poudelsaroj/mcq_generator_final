import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const ScoreCard = ({ score, total }) => {
  const percentage = ((score / total) * 100).toFixed(1);
  
  const getGrade = () => {
    if (percentage >= 90) return 'Excellent!';
    if (percentage >= 80) return 'Very Good!';
    if (percentage >= 70) return 'Good!';
    if (percentage >= 60) return 'Fair';
    return 'Needs Improvement';
  };

  return (
    <View style={styles.container}>
      <Text style={styles.grade}>{getGrade()}</Text>
      <Text style={styles.score}>{score}/{total}</Text>
      <Text style={styles.percentage}>{percentage}%</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 20,
    alignItems: 'center',
    margin: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
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
    color: '#666',
  }
});

export default ScoreCard;