import 'package:flutter/material.dart';
import 'package:timetracker_mobile/data/storage/sync_service.dart';
import 'package:timetracker_mobile/domain/usecases/sync_usecase.dart';

class FailedSyncScreen extends StatefulWidget {
  const FailedSyncScreen({super.key});

  @override
  State<FailedSyncScreen> createState() => _FailedSyncScreenState();
}

class _FailedSyncScreenState extends State<FailedSyncScreen> {
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final items = await SyncService.listFailed();
    if (!mounted) return;
    setState(() {
      _items = items;
      _loading = false;
    });
  }

  Future<void> _retry(String id) async {
    setState(() => _busy = true);
    await SyncService.retry(id);
    await SyncUseCase.shared.sync();
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _discard(String id) async {
    setState(() => _busy = true);
    await SyncService.discard(id);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sync problems'),
        actions: [
          IconButton(
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(child: Text('No failed sync items.'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final item = _items[index];
                    final id = item['id']?.toString() ?? '';
                    final type = item['op']?.toString() ?? 'unknown';
                    final error = item['lastError']?.toString() ?? '';
                    final attempts = (item['attempts'] as num?)?.toInt() ?? 0;
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(type, style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 4),
                            Text('$attempts attempts'),
                            if (error.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(error, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                            ],
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                FilledButton(
                                  onPressed: _busy || id.isEmpty ? null : () => _retry(id),
                                  child: const Text('Retry'),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  onPressed: _busy || id.isEmpty ? null : () => _discard(id),
                                  child: const Text('Discard'),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
