import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import HomeScreen from '../screens/HomeScreen';
import FileUploadScreen from '../screens/FileUploadScreen';
import MCQGeneratorScreen from '../screens/MCQGeneratorScreen';
import MCQOptionsScreen from '../screens/MCQOptionsScreen';
import MCQAssessmentScreen from '../screens/MCQAssessmentScreen';
import MCQResultScreen from '../screens/MCQResultScreen';
import ChatScreen from '../screens/ChatScreen';
import MCQScreen from '../screens/MCQScreen';
import NumQuestionsScreen from '../screens/NumQuestionsScreen';
import ChapterSelectionScreen from '../screens/ChapterSelectionScreen';
// import DetailsScreen from '../screens/DetailsScreen';

const Stack = createStackNavigator();

function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerStyle: {
          backgroundColor: '#007AFF',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen 
        name="Home" 
        component={HomeScreen}
        options={{ title: 'MCQ Generator' }}
      />
      <Stack.Screen 
        name="FileUpload" 
        component={FileUploadScreen}
        options={{ title: 'Upload File' }}
      />
      <Stack.Screen 
        name="MCQGenerator" 
        component={MCQGeneratorScreen}
        options={{ title: 'Generate MCQs' }}
      />
      <Stack.Screen 
        name="NumQuestions" 
        component={NumQuestionsScreen}
        options={{ title: 'Number of Questions' }}
      />
      <Stack.Screen 
        name="MCQOptions" 
        component={MCQOptionsScreen} 
        options={{ title: 'MCQ Options' }}
      />
      <Stack.Screen 
        name="MCQAssessment" 
        component={MCQAssessmentScreen}
        options={{ title: 'Assessment' }}
      />
      <Stack.Screen 
        name="MCQResult" 
        component={MCQResultScreen}
        options={{ title: 'Results' }}
      />
      <Stack.Screen 
        name="Chat" 
        component={ChatScreen}
        options={{ title: 'Chat' }}
      />
      <Stack.Screen 
        name="MCQScreen" 
        component={MCQScreen}
        options={{ title: 'Generated MCQs' }}
      />
      <Stack.Screen 
        name="ChapterSelection" 
        component={ChapterSelectionScreen}
        options={{ title: 'Select Chapters' }}
      />
      {/* <Stack.Screen 
        name="Details" 
        component={DetailsScreen}
      /> */}
    </Stack.Navigator>
  );
}

export default AppNavigator;