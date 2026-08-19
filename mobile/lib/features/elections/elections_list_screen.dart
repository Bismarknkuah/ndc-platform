import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'election_detail_screen.dart';
import 'elections_provider.dart';

class ElectionsListScreen extends StatefulWidget {
  const ElectionsListScreen({super.key});

  @override
  State<ElectionsListScreen> createState() => _ElectionsListScreenState();
}

class _ElectionsListScreenState extends State<ElectionsListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ElectionsProvider>().loadElections();
    });
  }

  Color _statusColor(String status, BuildContext context) {
    switch (status) {
      case 'OPEN':
        return Colors.green;
      case 'COLLATION':
        return Colors.orange;
      case 'COMPLETED':
        return Theme.of(context).disabledColor;
      default:
        return Theme.of(context).colorScheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ElectionsProvider>();
    final dateFormat = DateFormat('MMM d, yyyy');

    return Scaffold(
      appBar: AppBar(title: const Text('Elections & Polls')),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.elections.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.elections.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.elections.isEmpty) {
            return const Center(child: Text('No elections or polls yet.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<ElectionsProvider>().loadElections(),
            child: ListView.separated(
              itemCount: provider.elections.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final election = provider.elections[index];
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _statusColor(election.status, context),
                    child: Icon(
                      election.electionType == 'POLL' ? Icons.poll : Icons.how_to_vote,
                      color: Colors.white,
                    ),
                  ),
                  title: Text(election.title),
                  subtitle: Text(
                    '${election.electionType.replaceAll('_', ' ')} · '
                    '${dateFormat.format(election.startDate)} - ${dateFormat.format(election.endDate)}',
                  ),
                  trailing: Chip(label: Text(election.status)),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ElectionDetailScreen(
                        electionId: election.id,
                        title: election.title,
                      ),
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
