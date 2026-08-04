import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'events_provider.dart';

class EventsListScreen extends StatefulWidget {
  const EventsListScreen({super.key});

  @override
  State<EventsListScreen> createState() => _EventsListScreenState();
}

class _EventsListScreenState extends State<EventsListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<EventsProvider>().load();
    });
  }

  IconData _iconFor(String eventType) {
    switch (eventType) {
      case 'RALLY':
        return Icons.campaign;
      case 'TOWN_HALL':
        return Icons.forum;
      case 'FUNDRAISER':
        return Icons.volunteer_activism;
      case 'COMMUNITY_OUTREACH':
        return Icons.diversity_3;
      default:
        return Icons.event;
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<EventsProvider>();
    final dateFormat = DateFormat('EEE, MMM d - h:mm a');

    return Scaffold(
      appBar: AppBar(title: const Text('Upcoming Events')),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.events.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.events.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.events.isEmpty) {
            return const Center(child: Text('No upcoming events.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<EventsProvider>().load(),
            child: ListView.separated(
              padding: const EdgeInsets.all(8),
              itemCount: provider.events.length,
              separatorBuilder: (_, __) => const SizedBox(height: 4),
              itemBuilder: (context, index) {
                final event = provider.events[index];
                final rsvpStatus = provider.rsvpStatusFor(event.id);
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(child: Icon(_iconFor(event.eventType))),
                    title: Text(event.title),
                    subtitle: Text(
                      '${dateFormat.format(event.scheduledStart)}'
                      '${event.location.isNotEmpty ? '\n${event.location}' : ''}',
                    ),
                    isThreeLine: event.location.isNotEmpty,
                    trailing: provider.isRsvpInFlight(event.id)
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : rsvpStatus != null
                            ? Chip(label: Text(rsvpStatus))
                            : PopupMenuButton<String>(
                                icon: const Icon(Icons.event_available),
                                onSelected: (status) =>
                                    context.read<EventsProvider>().rsvp(event.id, status),
                                itemBuilder: (_) => const [
                                  PopupMenuItem(value: 'ATTENDING', child: Text('Attending')),
                                  PopupMenuItem(
                                    value: 'DECLINED',
                                    child: Text("Can't make it"),
                                  ),
                                ],
                              ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
