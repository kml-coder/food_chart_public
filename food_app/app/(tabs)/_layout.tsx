import { Tabs, Stack } from 'expo-router';
import React from 'react';
import { Platform} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';

import { HapticTab } from '@/components/HapticTab';
import { IconSymbol } from '@/components/ui/IconSymbol';
import TabBarBackground from '@/components/ui/TabBarBackground';
import { Colors } from '@/constants/Colors';
import { useColorScheme } from '@/hooks/useColorScheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarButton: HapticTab,
        tabBarBackground: TabBarBackground,
        tabBarStyle: Platform.select({
          ios: {
            // Use a transparent background on iOS to show the blur effect
            position: 'absolute',
          },
          default: {},
        }),
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size}) => (<Ionicons name="home-outline" size={size} color={color} />),
        }}
      />
      <Tabs.Screen
        name="button"
        options={{
          title: 'Button',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="paperplane.fill" color={color} />,
        }}
      />
            <Tabs.Screen
        name="food_main"
        options={{
          title: 'Food Main',
          tabBarIcon: ({ color, size}) => (<Ionicons name= "fast-food-outline" size={size} color={color} />),
        }}
      />
            <Tabs.Screen
        name="recipe_pie"
        options={{
          title: 'Recipe Pie',
          tabBarIcon: ({ color, size}) => (<Ionicons name="pie-chart-outline" size={size} color={color} />),
        }}
      />
    </Tabs>
  );
}
