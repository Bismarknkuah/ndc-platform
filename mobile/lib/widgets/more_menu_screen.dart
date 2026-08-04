import 'package:flutter/material.dart';

import '../features/direct_messages/direct_messages_inbox_screen.dart';
import '../features/elections/elections_list_screen.dart';
import '../features/events/events_list_screen.dart';
import '../features/groups/groups_list_screen.dart';
import '../features/membership/membership_card_screen.dart';
import '../features/volunteers/volunteer_opportunities_screen.dart';
import '../features/welfare/welfare_screen.dart';

class MoreMenuScreen extends StatelessWidget {
  const MoreMenuScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = <_MenuItem>[
      _MenuItem(
        icon: Icons.badge,
        label: 'Membership Card',
        builder: (_) => const MembershipCardScreen(),
      ),
      _MenuItem(
        icon: Icons.how_to_vote,
        label: 'Elections & Polls',
        builder: (_) => const ElectionsListScreen(),
      ),
      _MenuItem(
        icon: Icons.event,
        label: 'Events',
        builder: (_) => const EventsListScreen(),
      ),
      _MenuItem(
        icon: Icons.volunteer_activism,
        label: 'Volunteer',
        builder: (_) => const VolunteerOpportunitiesScreen(),
      ),
      _MenuItem(
        icon: Icons.favorite,
        label: 'Welfare Support',
        builder: (_) => const WelfareScreen(),
      ),
      _MenuItem(
        icon: Icons.forum,
        label: 'Discussion Groups',
        builder: (_) => const GroupsListScreen(),
      ),
      _MenuItem(
        icon: Icons.mail,
        label: 'Messages',
        builder: (_) => const DirectMessagesInboxScreen(),
      ),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        children: items
            .map(
              (item) => Card(
                child: InkWell(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: item.builder),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(item.icon, size: 40),
                      const SizedBox(height: 8),
                      Text(item.label, textAlign: TextAlign.center),
                    ],
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

class _MenuItem {
  _MenuItem({required this.icon, required this.label, required this.builder});

  final IconData icon;
  final String label;
  final WidgetBuilder builder;
}
