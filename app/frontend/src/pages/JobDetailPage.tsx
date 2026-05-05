import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, Image as ImageIcon, FileText, AlertCircle } from 'lucide-react';

interface JobDetail {
  message_id: string;
  status: 'pending' | 'finished' | 'failed' | 'unknown';
  job_type: string;
  filename: string;
  email: string | null;
  session_id: string | null;
  content: string | null;
  segments_count: number | null;
  error: string | null;
}

export const JobDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const { token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchJobDetail = async () => {
      if (!token || !id) return;
      
      try {
        const response = await fetch(`/admin/api/jobs/${id}`, {
          headers: {
            'X-Dashboard-Token': token,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Unauthorized');
          }
          if (response.status === 404) {
            throw new Error('Job not found');
          }
          throw new Error('Failed to fetch job details');
        }

        const data = await response.json();
        setJob(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching job details:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobDetail();
    
    const intervalId = setInterval(() => {
      if (job?.status === 'pending') {
        fetchJobDetail();
      }
    }, 5000);
    
    return () => clearInterval(intervalId);
  }, [id, token, job?.status]);

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

  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="pl-0">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="flex flex-col items-center justify-center p-12 text-red-500">
            <AlertCircle className="mb-4 h-12 w-12" />
            <h2 className="text-xl font-bold">Error Loading Job</h2>
            <p className="mt-2">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading || !job) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-40" />
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-1/3" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" className="pl-0" render={<Link to="/dashboard" />}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Dashboard
      </Button>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-2xl font-bold break-all">
              Job: {job.message_id}
            </CardTitle>
            <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{job.filename || 'Unknown file'}</span>
              <span>•</span>
              <span>{job.email || 'No email'}</span>
              <span>•</span>
              <span>Session: {job.session_id || 'None'}</span>
            </div>
          </div>
          <div>
            {getStatusBadge(job.status)}
          </div>
        </CardHeader>
        <CardContent>
          {job.status === 'failed' && job.error && (
            <div className="mb-6 rounded-md bg-red-50 p-4 text-red-500 border border-red-200">
              <h4 className="font-semibold flex items-center">
                <AlertCircle className="mr-2 h-4 w-4" />
                Error Details
              </h4>
              <p className="mt-1 text-sm">{job.error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h3 className="text-lg font-semibold flex items-center">
                <ImageIcon className="mr-2 h-5 w-5" />
                Original Image
              </h3>
              <Separator />
              <div className="rounded-md border bg-muted/30 p-2 flex items-center justify-center min-h-[300px] overflow-hidden">
                {!imageError ? (
                  <img 
                    src={`/admin/api/images/${job.message_id}`} 
                    alt={job.filename || 'Uploaded image'} 
                    className="max-w-full max-h-[500px] object-contain rounded"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="text-center text-muted-foreground flex flex-col items-center">
                    <ImageIcon className="h-12 w-12 mb-2 opacity-20" />
                    <p>Image not available</p>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-semibold flex items-center justify-between">
                <div className="flex items-center">
                  <FileText className="mr-2 h-5 w-5" />
                  Extracted Text
                </div>
                {job.segments_count !== null && (
                  <Badge variant="outline" className="font-normal">
                    {job.segments_count} segments
                  </Badge>
                )}
              </h3>
              <Separator />
              <div className="rounded-md border bg-muted/10 p-4 min-h-[300px] max-h-[500px] overflow-y-auto whitespace-pre-wrap font-mono text-sm">
                {job.status === 'pending' ? (
                  <div className="flex h-full items-center justify-center text-muted-foreground italic">
                    Processing image...
                  </div>
                ) : job.content ? (
                  job.content
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground italic">
                    No text extracted
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
