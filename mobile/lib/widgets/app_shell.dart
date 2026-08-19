import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../features/auth/auth_provider.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/notifications/notifications_screen.dart';
import 'more_menu_screen.dart';

/// Post-login shell: bottom navigation between the screens this scaffold
/// ships with. Add more tabs here (or more tiles in MoreMenuScreen) as
/// more feature screens land.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;

  final List<Widget> _screens = const [
    _DashboardTab(),
    NotificationsScreen(),
    MoreMenuScreen(),
    _ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _selectedIndex, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
          NavigationDestination(
            icon: Icon(Icons.notifications),
            label: 'Notifications',
          ),
          NavigationDestination(icon: Icon(Icons.apps), label: 'More'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class _DashboardTab extends StatelessWidget {
  const _DashboardTab();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('NDC Dashboard')),
      body: const DashboardScreen(),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.currentUser;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: CircleAvatar(
              radius: 40,
              child: Text(
                (user?.fullName.isNotEmpty ?? false)
                    ? user!.fullName.substring(0, 1)
                    : '?',
                style: const TextStyle(fontSize: 32),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text(
              user?.fullName ?? '',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          Center(child: Text(user?.email ?? '')),
          const SizedBox(height: 24),
          ListTile(
            leading: const Icon(Icons.badge),
            title: const Text('Membership ID'),
            subtitle: Text(user?.membershipId ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.work),
            title: const Text('Role'),
            subtitle: Text(user?.role?.name ?? 'Ordinary Member'),
          ),
          ListTile(
            leading: const Icon(Icons.location_on),
            title: const Text('Organizational Unit'),
            subtitle: Text(user?.organizationalUnit?.name ?? ''),
          ),
          const SizedBox(height: 24),
          FilledButton.tonal(
            onPressed: () => context.read<AuthProvider>().logout(),
            child: const Text('Log Out'),
          ),
        ],
      ),
    );
  }
}
