import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { BaseService } from './base.service';

@Injectable({
  providedIn: 'root'
})
export class ChatService extends BaseService {
  constructor(protected override http: HttpClient) {
    super(http);
  }

  sendMessage(question: string): Observable<any> {
    const endpoint = `${this.baseUrl}/chat`;
    return this.http.post(endpoint, { question }).pipe(
      catchError((error) => {
        console.error('ChatService error:', error);
        throw error;
      })
    );
  }
}
