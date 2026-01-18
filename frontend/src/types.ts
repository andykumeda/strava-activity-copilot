export interface User {
    id: number;
    name: string;
    strava_id: number;
    profile_picture: string;
    connected: boolean;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    data?: any; // For charts/visuals if we implement them
}
