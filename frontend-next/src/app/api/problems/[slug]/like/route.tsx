import { NextRequest, NextResponse } from "next/server";

interface LikeResponse {
    like: number;
    dislike: number;
    user_reaction: boolean;
}

export async function GET(request:NextRequest) {
    return
}