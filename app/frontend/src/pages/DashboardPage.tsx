import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface Job {
  message_id: string;
  status: 'pending' | 'finished' | 'failed' | 'unknown';
  job_type: string;
  filename: string;
  email: string | null;
  session_id: string | null;
}

export const DashboardPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const { token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchJobs = async () => {
      if (!token) return;
      
      try {
        const response = await fetch('/admin/api/jobs', {
          headers: {
            'X-Dashboard-Token': token,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Unauthorized');
          }
          throw new Error('Failed to fetch jobs');
        }

        const data = await response.json();
        setJobs(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching jobs:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
    
    const intervalId = setInterval(fetchJobs, 5000);
    
    return () => clearInterval(intervalId);
  }, [token]);

  const filteredJobs = jobs.filter(job => {
    if (statusFilter === 'all') return true;
    return job.status === statusFilter;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'finished':
        return <Badge className="bg-green-500 hover:bg-green-600">Finished</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500 hover:bg-yellow-600 text-white">Pending</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Jobs</h2>
        <div className="flex items-center gap-2">
          <select 
            className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="finished">Finished</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Recent Conversions</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="p-4 text-center text-red-500 bg-red-50 rounded-md">
              {error}
            </div>
          ) : isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No jobs found matching the current filter.
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Filename</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Session ID</TableHead>
                    <TableHead className="text-right">ID</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredJobs.map((job) => (
                    <TableRow 
                      key={job.message_id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/dashboard/jobs/${job.message_id}`)}
                    >
                      <TableCell>{getStatusBadge(job.status)}</TableCell>
                      <TableCell className="font-medium truncate max-w-[200px]" title={job.filename}>
                        {job.filename || 'Unknown'}
                      </TableCell>
                      <TableCell>{job.email || '-'}</TableCell>
                      <TableCell className="truncate max-w-[150px]" title={job.session_id || ''}>
                        {job.session_id || '-'}
                      </TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground truncate max-w-[100px]" title={job.message_id}>
                        {job.message_id.substring(0, 8)}...
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
