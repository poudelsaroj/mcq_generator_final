import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'react-native';
// Import AppNavigator properly - make sure it's exported correctly
import AppNavigator from './navigation/AppNavigator';

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar backgroundColor="#007AFF" barStyle="light-content" />
      <AppNavigator />
    </NavigationContainer>
  );
}