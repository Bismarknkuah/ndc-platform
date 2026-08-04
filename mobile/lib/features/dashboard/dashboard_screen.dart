import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'dashboard_provider.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DashboardProvider>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();

    if (provider.isLoading && provider.data == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (provider.error != null && provider.data == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(provider.error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.read<DashboardProvider>().load(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final data = provider.data!;
    final dateFormat = DateFormat('EEE, MMM d - h:mm a');

    return RefreshIndicator(
      onRefresh: () => context.read<DashboardProvider>().load(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Welcome, ${data.profile.fullName}',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text(
            '${data.profile.role?.name ?? 'Member'} · '
            '${data.profile.organizationalUnit?.name ?? ''}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),

          if (data.teamsLed != null) ...[
            const _SectionHeader('Teams You Lead'),
            ...data.teamsLed!.map(
              (team) => Card(
                child: ListTile(
                  leading: const Icon(Icons.groups),
                  title: Text('${team.departmentName} - ${team.unitName}'),
                  subtitle: Text(
                    '${team.position} · ${team.teamSize} members · '
                    '${team.pendingTasks} pending tasks',
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          _SectionHeader(
            'Upcoming Meetings',
            trailing: data.upcomingMeetings.isEmpty
                ? null
                : '${data.upcomingMeetings.length}',
          ),
          if (data.upcomingMeetings.isEmpty)
            const _EmptyRow('No upcoming meetings.')
          else
            ...data.upcomingMeetings.map(
              (meeting) => Card(
                child: ListTile(
                  leading: Icon(
                    meeting.meetingType == 'WORKSHOP'
                        ? Icons.school
                        : Icons.video_call,
                  ),
                  title: Text(meeting.title),
                  subtitle: Text(dateFormat.format(meeting.scheduledStart)),
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
            ),
          const SizedBox(height: 16),

          _SectionHeader(
            'Pending Tasks',
            trailing: data.pendingTasks.isEmpty
                ? null
                : '${data.pendingTasks.length}',
          ),
          if (data.pendingTasks.isEmpty)
            const _EmptyRow('No pending tasks.')
          else
            ...data.pendingTasks.map(
              (task) => Card(
                child: ListTile(
                  leading: const Icon(Icons.assignment),
                  title: Text(task.title),
                  subtitle: Text(
                    '${task.engagementType} · ${task.platformName} · '
                    '${dateFormat.format(task.scheduledAt)}',
                  ),
                ),
              ),
            ),

          if (data.activeElections != null &&
              data.activeElections!.isNotEmpty) ...[
            const SizedBox(height: 16),
            const _SectionHeader('Active Elections'),
            ...data.activeElections!.map(
              (election) => Card(
                child: ListTile(
                  leading: const Icon(Icons.how_to_vote),
                  title: Text(election['title'] as String? ?? ''),
                  subtitle: Text(election['status'] as String? ?? ''),
                ),
              ),
            ),
          ],

          if (data.upcomingEvents != null &&
              data.upcomingEvents!.isNotEmpty) ...[
            const SizedBox(height: 16),
            const _SectionHeader('Upcoming Events'),
            ...data.upcomingEvents!.map(
              (event) => Card(
                child: ListTile(
                  leading: const Icon(Icons.event),
                  title: Text(event['title'] as String? ?? ''),
                  subtitle: Text(event['location'] as String? ?? ''),
                ),
              ),
            ),
          ],

          if (data.financeSummary != null) ...[
            const SizedBox(height: 16),
            const _SectionHeader('Finance Summary'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _FinanceLine(
                      'Income',
                      data.financeSummary!['total_income'].toString(),
                    ),
                    _FinanceLine(
                      'Expense',
                      data.financeSummary!['total_expense'].toString(),
                    ),
                    _FinanceLine(
                      'Net Balance',
                      data.financeSummary!['net_balance'].toString(),
                      emphasize: true,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title, {this.trailing});

  final String title;
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          if (trailing != null)
            Chip(
              label: Text(trailing!),
              visualDensity: VisualDensity.compact,
            ),
        ],
      ),
    );
  }
}

class _EmptyRow extends StatelessWidget {
  const _EmptyRow(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        message,
        style: Theme.of(context)
            .textTheme
            .bodyMedium
            ?.copyWith(color: Theme.of(context).hintColor),
      ),
    );
  }
}

class _FinanceLine extends StatelessWidget {
  const _FinanceLine(this.label, this.value, {this.emphasize = false});

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    final style = emphasize
        ? Theme.of(context)
            .textTheme
            .titleMedium
            ?.copyWith(fontWeight: FontWeight.bold)
        : Theme.of(context).textTheme.bodyMedium;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: style),
          Text('GHS $value', style: style),
        ],
      ),
    );
  }
}
