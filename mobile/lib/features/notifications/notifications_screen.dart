import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'notifications_provider.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<NotificationsProvider>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<NotificationsProvider>();
    final dateFormat = DateFormat('MMM d, h:mm a');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: () => context.read<NotificationsProvider>().markAllRead(),
            child: const Text('Mark all read'),
          ),
        ],
      ),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.notifications.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.notifications.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.notifications.isEmpty) {
            return const Center(child: Text('No notifications yet.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<NotificationsProvider>().load(),
            child: ListView.separated(
              itemCount: provider.notifications.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final notification = provider.notifications[index];
                return ListTile(
                  leading: Icon(
                    _iconFor(notification.notificationType),
                    color: notification.isRead
                        ? Theme.of(context).disabledColor
                        : Theme.of(context).colorScheme.primary,
                  ),
                  title: Text(
                    notification.title,
                    style: TextStyle(
                      fontWeight:
                          notification.isRead ? FontWeight.normal : FontWeight.bold,
                    ),
                  ),
                  subtitle: Text(
                    '${notification.body}\n${dateFormat.format(notification.createdAt)}',
                  ),
                  isThreeLine: true,
                  onTap: () {
                    if (!notification.isRead) {
                      context.read<NotificationsProvider>().markRead(notification.id);
                    }
                  },
                );
              },
            ),
          );
        },
      ),
    );
  }

  IconData _iconFor(String type) {
    switch (type) {
      case 'BROADCAST':
        return Icons.campaign;
      case 'REPORT':
        return Icons.assignment_turned_in;
      case 'DIRECT_MESSAGE':
        return Icons.mail;
      case 'GROUP_MESSAGE':
        return Icons.forum;
      case 'TASK':
        return Icons.task_alt;
      case 'MEETING':
        return Icons.video_call;
      case 'ELECTION_ELIGIBILITY':
        return Icons.how_to_vote;
      case 'EVENT':
        return Icons.event;
      default:
        return Icons.notifications;
    }
  }
}
