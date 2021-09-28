import 'package:flutter/material.dart';
import 'home_page.dart';
//import 'login_page.dart';

void main() {
  runApp(MaterialApp(
    title: 'Named Route Navigation',
    theme: ThemeData(
      // This is the theme of your application.
      primarySwatch: Colors.lightGreen,
    ),
    // Start the app with the "/" named route. In this case, the app starts
    // on the FirstScreen widget.
    initialRoute: '/',
    routes: {
      // When navigating to the "/" route, build the FirstScreen widget.
      '/': (context) => const HomeScreen(),
      // When navigating to the "/second" route, build the SecondScreen widget.
      //'/second': (context) => const SecondScreen(),
    },
  ));
}
