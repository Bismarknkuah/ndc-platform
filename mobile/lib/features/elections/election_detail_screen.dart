import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'election_models.dart';
import 'elections_provider.dart';

class ElectionDetailScreen extends StatelessWidget {
  const ElectionDetailScreen({super.key, required this.electionId, required this.title});

  final String electionId;
  final String title;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ElectionDetailProvider()..load(electionId),
      child: _ElectionDetailView(electionId: electionId, title: title),
    );
  }
}

class _ElectionDetailView extends StatelessWidget {
  const _ElectionDetailView({required this.electionId, required this.title});

  final String electionId;
  final String title;

  Map<String?, List<Candidate>> _groupByRace(List<Candidate> candidates) {
    final races = <String?, List<Candidate>>{};
    for (final candidate in candidates) {
      races.putIfAbsent(candidate.position, () => []).add(candidate);
    }
    return races;
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ElectionDetailProvider>();

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.candidates.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.candidates.isEmpty) {
            return Center(child: Text(provider.error!));
          }

          final eligibility = provider.eligibility;
          final races = _groupByRace(provider.candidates);

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (eligibility != null && !eligibility.eligible)
                const Card(
                  color: Color(0xFFFFF3E0),
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      "You're not on the electorate for this election - you "
                      "can view the candidates, but voting is disabled.",
                    ),
                  ),
                ),
              if (eligibility != null && eligibility.eligible && eligibility.electionStatus != 'OPEN')
                Card(
                  color: const Color(0xFFFFF3E0),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text('Voting is not open yet (status: ${eligibility.electionStatus}).'),
                  ),
                ),
              const SizedBox(height: 8),
              for (final entry in races.entries)
                _RaceCard(
                  electionId: electionId,
                  position: entry.key,
                  candidates: entry.value,
                  canVote: eligibility?.eligible == true && eligibility?.electionStatus == 'OPEN',
                  alreadyVoted: eligibility?.hasVotedFor(entry.key) ?? false,
                ),
            ],
          );
        },
      ),
    );
  }
}

class _RaceCard extends StatefulWidget {
  const _RaceCard({
    required this.electionId,
    required this.position,
    required this.candidates,
    required this.canVote,
    required this.alreadyVoted,
  });

  final String electionId;
  final String? position;
  final List<Candidate> candidates;
  final bool canVote;
  final bool alreadyVoted;

  @override
  State<_RaceCard> createState() => _RaceCardState();
}

class _RaceCardState extends State<_RaceCard> {
  String? _selectedCandidateId;

  Future<void> _submitVote() async {
    if (_selectedCandidateId == null) return;
    final provider = context.read<ElectionDetailProvider>();
    final success = await provider.castVote(widget.electionId, _selectedCandidateId!, widget.position);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? 'Vote cast successfully.' : (provider.lastVoteError ?? 'Vote failed.')),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ElectionDetailProvider>();

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.position ?? 'Result',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (widget.alreadyVoted)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('You have already voted in this race.'),
              ),
            const SizedBox(height: 8),
            for (final candidate in widget.candidates)
              RadioListTile<String>(
                value: candidate.id,
                groupValue: _selectedCandidateId,
                onChanged: (widget.canVote && !widget.alreadyVoted)
                    ? (value) => setState(() => _selectedCandidateId = value)
                    : null,
                secondary: candidate.photoBase64 != null
                    ? CircleAvatar(backgroundImage: MemoryImage(base64Decode(candidate.photoBase64!)))
                    : const CircleAvatar(child: Icon(Icons.person)),
                title: Text(candidate.name),
                subtitle: candidate.party != null ? Text(candidate.party!) : null,
              ),
            if (widget.canVote && !widget.alreadyVoted)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton(
                  onPressed: (_selectedCandidateId == null || provider.isVoting) ? null : _submitVote,
                  child: provider.isVoting
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Cast Vote'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
