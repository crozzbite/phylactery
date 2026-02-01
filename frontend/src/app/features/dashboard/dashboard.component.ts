import { Component, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { UpperCasePipe, CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { GlassCardComponent } from '../../shared/components/glass-card.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge.component';
import { NeuralSpineComponent } from './components/neural-spine/neural-spine.component';
import { SidebarComponent } from './components/sidebar/sidebar.component';
import { ArtifactsSidebarComponent } from '../artifacts/artifacts-sidebar.component';
import { ArtifactRendererComponent } from '../artifacts/artifact-renderer.component';
import { Artifact, ArtifactService } from '../../core/services/artifact.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    UpperCasePipe, 
    GlassCardComponent, 
    StatusBadgeComponent, 
    NeuralSpineComponent, 
    SidebarComponent,
    ArtifactsSidebarComponent,
    ArtifactRendererComponent
  ],
  templateUrl: './dashboard.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardComponent {
  public authService = inject(AuthService);
  public artifactService = inject(ArtifactService);
  isRightSidebarOpen = signal(true);
  
  logout() {
    this.authService.logout();
  }
  
  toggleRightSidebar() {
    this.isRightSidebarOpen.update(v => !v);
  }
}
