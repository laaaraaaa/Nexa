"use client";

import { useEffect, useState } from "react";

interface Memory {
  id: string;
  repo: string;
  workflow_name: string;
  error_type: string;
  error_message: string;
  fix_attempted: string;
  fix_successful: boolean;
  pr_number: number | null;
  created_at: string;
}

interface Stats {
  total_failures: number;
  fixes_attempted: number;
  fixes_successful: number;
  success_rate: number;
}

export default function Home() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [memoriesRes, statsRes] = await Promise.all([
          fetch("http://localhost:8000/api/memories"),
          fetch("http://localhost:8000/api/stats"),
        ]);

        const memoriesData = await memoriesRes.json();
        const statsData = await statsRes.json();

        setMemories(memoriesData);
        setStats(statsData);
      } catch (err) {
        console.error("Failed to fetch data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Nexa Dashboard</h1>
        <p className="text-gray-400 mt-1">
          Autonomous CI/CD healing agent — memory explorer
        </p>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm">Total Failures</p>
            <p className="text-3xl font-bold text-white mt-1">
              {stats.total_failures}
            </p>
          </div>

          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm">Fixes Attempted</p>
            <p className="text-3xl font-bold text-blue-400 mt-1">
              {stats.fixes_attempted}
            </p>
          </div>

          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm">Fixes Successful</p>
            <p className="text-3xl font-bold text-green-400 mt-1">
              {stats.fixes_successful}
            </p>
          </div>

          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm">Success Rate</p>
            <p className="text-3xl font-bold text-purple-400 mt-1">
              {stats.success_rate}%
            </p>
          </div>
        </div>
      )}

      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Memory Explorer</h2>
          <p className="text-gray-400 text-sm">
            All episodic memories — failures, fixes, and outcomes
          </p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-400">
            Loading memories...
          </div>
        ) : memories.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            No memories yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-800">
                  <th className="p-4">Repo</th>
                  <th className="p-4">Error Type</th>
                  <th className="p-4">Fix Attempted</th>
                  <th className="p-4">PR</th>
                  <th className="p-4">Outcome</th>
                  <th className="p-4">Time</th>
                </tr>
              </thead>

              <tbody>
                {memories.map((m) => (
                  <tr
                    key={m.id}
                    className="border-b border-gray-800 hover:bg-gray-800 transition-colors"
                  >
                    <td className="p-4 text-sm font-mono text-blue-300">
                      {m.repo}
                    </td>

                    <td className="p-4">
                      <span className="bg-gray-800 text-yellow-300 text-xs px-2 py-1 rounded-full">
                        {m.error_type || "unknown"}
                      </span>
                    </td>

                    <td className="p-4 text-sm text-gray-300 max-w-xs truncate">
                      {m.fix_attempted || "—"}
                    </td>

                    <td className="p-4 text-sm">
                      {m.pr_number ? (
                        <a
                          href={`https://github.com/${m.repo}/pull/${m.pr_number}`}
                          target="_blank"
                          className="text-blue-400 hover:underline"
                        >
                          #{m.pr_number}
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>

                    <td className="p-4">
                      {m.pr_number ? (
                        m.fix_successful ? (
                          <span className="bg-green-900 text-green-300 text-xs px-2 py-1 rounded-full">
                            Fixed
                          </span>
                        ) : (
                          <span className="bg-red-900 text-red-300 text-xs px-2 py-1 rounded-full">
                            Failed
                          </span>
                        )
                      ) : (
                        <span className="bg-gray-800 text-gray-400 text-xs px-2 py-1 rounded-full">
                          Analyzed
                        </span>
                      )}
                    </td>

                    <td className="p-4 text-sm text-gray-400">
                      {m.created_at
                        ? new Date(m.created_at).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}