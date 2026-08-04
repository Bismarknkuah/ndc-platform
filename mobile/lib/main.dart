import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'features/auth/auth_provider.dart';
import 'features/auth/login_screen.dart';
import 'features/dashboard/dashboard_provider.dart';
import 'features/direct_messages/direct_messages_provider.dart';
import 'features/elections/elections_provider.dart';
import 'features/events/events_provider.dart';
import 'features/groups/groups_provider.dart';
import 'features/membership/membership_card_provider.dart';
import 'features/notifications/notifications_provider.dart';
import 'features/volunteers/volunteer_provider.dart';
import 'features/welfare/welfare_provider.dart';
import 'widgets/app_shell.dart';

void main() {
  runApp(const NdcApp());
}

class NdcApp extends StatelessWidget {
  const NdcApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()..restoreSession()),
        ChangeNotifierProvider(create: (_) => DashboardProvider()),
        ChangeNotifierProvider(create: (_) => NotificationsProvider()),
        ChangeNotifierProvider(create: (_) => MembershipCardProvider()),
        ChangeNotifierProvider(create: (_) => ElectionsProvider()),
        ChangeNotifierProvider(create: (_) => EventsProvider()),
        ChangeNotifierProvider(create: (_) => VolunteerProvider()),
        ChangeNotifierProvider(create: (_) => WelfareProvider()),
        ChangeNotifierProvider(create: (_) => GroupsProvider()),
        ChangeNotifierProvider(create: (_) => DirectMessagesInboxProvider()),
      ],
      child: MaterialApp(
        title: 'NDC Member Portal',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorSchemeSeed: const Color(0xFF057B45), // NDC green
          useMaterial3: true,
        ),
        home: const _RootRouter(),
      ),
    );
  }
}

/// Decides between the login flow and the main app shell based on the
/// current session, and shows a splash spinner while that's unknown.
class _RootRouter extends StatelessWidget {
  const _RootRouter();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    switch (auth.status) {
      case AuthStatus.unknown:
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      case AuthStatus.unauthenticated:
        return const LoginScreen();
      case AuthStatus.authenticated:
        return const AppShell();
    }
  }
}
